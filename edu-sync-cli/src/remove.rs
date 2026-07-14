use dialoguer::Select;
use edu_sync::config::Config;
use tokio::task;

/// Removes an existing account interactively.
#[derive(Debug, clap::Parser)]
pub struct Subcommand {}

impl Subcommand {
    pub async fn run(self) -> anyhow::Result<()> {
        // Read the main configuration file asynchronously
        let mut config = Config::read().await?;
        
        // If there are no accounts, there's nothing to remove
        if config.accounts.is_empty() {
            println!("No accounts configured.");
            return Ok(());
        }

        // Prepare lists to hold the IDs and the display strings for the interactive menu
        let mut account_ids: Vec<String> = Vec::new();
        let mut items = Vec::new();

        for (id, account) in &config.accounts {
            account_ids.push(id.clone());
            items.push(format!("{} (ID: {})", account, id));
        }

        // Prompt the user with an interactive terminal menu using dialoguer
        // We run this in a blocking task because dialoguer is synchronous and blocks the thread
        let selection = task::spawn_blocking(move || {
            Select::new()
                .with_prompt("Select account to remove")
                .items(&items)
                .default(0) // Start with the first item highlighted
                .interact()
        })
        .await??;

        // Retrieve the selected account ID based on the user's choice
        let selected_id = &account_ids[selection];
        
        // Remove the account from the in-memory config and, if successful, write it to disk
        if let Some(removed) = config.accounts.remove(selected_id) {
            config.write().await?;
            println!("Successfully removed account: {}", removed);
        }

        Ok(())
    }
}
