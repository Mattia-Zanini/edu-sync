use edu_sync::config::Config;

/// Lists all configured accounts.
#[derive(Debug, clap::Parser)]
pub struct Subcommand {}

impl Subcommand {
    pub async fn run(self) -> anyhow::Result<()> {
        // Read the main configuration file asynchronously
        let config = Config::read().await?;
        
        // If there are no accounts configured, print a message and exit early
        if config.accounts.is_empty() {
            println!("No accounts configured.");
            return Ok(());
        }

        println!("Configured accounts:");
        // Iterate over all accounts in the BTreeMap and display them with a 1-based index
        for (idx, (id, account)) in config.accounts.iter().enumerate() {
            println!("  [{}] {} (ID: {})", idx + 1, account, id);
        }

        Ok(())
    }
}
