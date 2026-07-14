use dialoguer::{Password, Select};
use edu_sync::{
    account::Account,
    config::{self, Config},
};
use std::path::PathBuf;
use tokio::task;

/// Updates the credentials (token or password) or sync directory of an existing account.
#[derive(Debug, clap::Parser)]
pub struct Subcommand {
    /// The username of the account.
    ///
    /// If set, you will be prompted for the corresponding password which will be
    /// used to retrieve the new token. If unset, you must supply the new token
    /// yourself (or leave it empty to keep the current token).
    #[structopt(short, long)]
    username: Option<String>,

    /// The new path to download resources to (optional).
    #[arg(short, long, value_hint = clap::ValueHint::DirPath)]
    path: Option<PathBuf>,
}

impl Subcommand {
    pub async fn run(self) -> anyhow::Result<()> {
        // Read the main configuration file asynchronously
        let mut config = Config::read().await?;
        
        // Return early if no accounts exist
        if config.accounts.is_empty() {
            println!("No accounts configured.");
            return Ok(());
        }

        // Prepare lists for the interactive selection menu
        let mut account_ids: Vec<String> = Vec::new();
        let mut items = Vec::new();

        for (id, account) in &config.accounts {
            account_ids.push(id.clone());
            items.push(format!("{} (ID: {})", account, id));
        }

        // Prompt the user to select which account to update using dialoguer
        let selection = task::spawn_blocking(move || {
            Select::new()
                .with_prompt("Select account to update")
                .items(&items)
                .default(0)
                .interact()
        })
        .await??;

        let selected_id = account_ids[selection].clone();
        
        // We need the site URL to perform login if a username is provided.
        // It's available in the existing account config.
        let site_url = config.accounts[&selected_id].id.site_url.clone();

        // Determine if we need to update the token, and if so, how.
        let token_opt = if let Some(username) = self.username {
            // Option A: The user provided a username, so we prompt for a password
            // and fetch a completely new token from the server via SSO/Login.
            let password =
                task::spawn_blocking(|| Password::new().with_prompt("Password").interact())
                    .await??;
            Some(Account::login(&site_url, &username, &password).await?.token)
        } else {
            // Option B: No username was provided. We prompt the user to manually paste a token.
            // If they just press Enter (empty string), we retain the current token.
            let token_str = task::spawn_blocking(|| {
                Password::new()
                    .with_prompt("New Token (leave empty to keep current)")
                    .allow_empty_password(true) // Crucial to allow skipping
                    .interact()
            })
            .await??;

            if token_str.trim().is_empty() {
                None // User chose not to update the token
            } else {
                Some(token_str.parse()?)
            }
        };

        // If the user specified a new path via `--path`, expand any shell variables (like ~)
        let new_path_opt = if let Some(p) = self.path {
            Some(config::expand_path(&p)?)
        } else {
            None
        };

        let mut success_msg = String::new();
        
        // Safely mutate the selected account in the BTreeMap
        if let Some(account) = config.accounts.get_mut(&selected_id) {
            // Update token if one was provided/fetched
            if let Some(token) = token_opt {
                account.token = token;
            }
            // Update the sync directory path if specified
            if let Some(new_path) = new_path_opt {
                account.path = new_path;
            }
            // Prepare a success message to display AFTER we write to disk
            // This prevents holding a mutable borrow across an await point.
            success_msg = format!("Successfully updated account: {}", account);
        }

        // Write the updated configuration to the disk
        if !success_msg.is_empty() {
            config.write().await?;
            println!("{}", success_msg);
        }

        Ok(())
    }
}
