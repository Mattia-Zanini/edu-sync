// Modificato il 2026-07-15: Aggiunto logging su file tramite tracing-appender (conformità GPLv3).
//! Moodle synchronization utility (CLI).

#![warn(rust_2018_idioms)]
#![warn(clippy::default_trait_access)]
#![warn(clippy::inconsistent_struct_constructor)]
#![warn(clippy::semicolon_if_nothing_returned)]
#![deny(rustdoc::all)]

mod add;
mod config;
mod fetch;
mod sync;
mod list;
mod remove;
mod update;
mod util;

use std::env;

use clap::CommandFactory;
use human_panic::setup_panic;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Layer};

#[derive(Debug, clap::Parser)]
#[clap(name = "edu-sync-cli", author, about, version)]
enum Subcommand {
    Add(add::Subcommand),
    Config(config::Subcommand),
    Fetch(fetch::Subcommand),
    Sync(sync::Subcommand),
    List(list::Subcommand),
    Remove(remove::Subcommand),
    Update(update::Subcommand),
}

impl Subcommand {
    async fn run(self) -> anyhow::Result<()> {
        match self {
            Subcommand::Add(command) => command.run().await,
            Subcommand::Config(command) => command.run().await,
            Subcommand::Fetch(command) => command.run().await,
            Subcommand::Sync(command) => command.run().await,
            Subcommand::List(command) => command.run().await,
            Subcommand::Remove(command) => command.run().await,
            Subcommand::Update(command) => command.run().await,
        }
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    clap_complete::CompleteEnv::with_factory(crate::Subcommand::command).complete();

    let log_dir = edu_sync::util::project_dirs().data_dir();
    std::fs::create_dir_all(log_dir).unwrap_or_default();
    let file_appender = tracing_appender::rolling::never(log_dir, "edu-sync-cli.log");
    let (non_blocking_file, _guard) = tracing_appender::non_blocking(file_appender);

    let file_layer = tracing_subscriber::fmt::layer()
        .with_writer(non_blocking_file)
        .with_ansi(false)
        .with_filter(EnvFilter::new("debug"));

    let stderr_filter = if env::var_os(EnvFilter::DEFAULT_ENV).is_some() {
        EnvFilter::try_from_default_env()?
    } else {
        EnvFilter::new("info")
    };

    let stderr_layer = tracing_subscriber::fmt::layer()
        .with_writer(std::io::stderr)
        .with_filter(stderr_filter);

    tracing_subscriber::registry()
        .with(file_layer)
        .with(stderr_layer)
        .init();

    setup_panic!();

    let log_path = log_dir.join("edu-sync-cli.log");
    let log_status = if log_path.exists() { "Exists" } else { "Not found" };
    
    let config_path = edu_sync::config::Config::path();
    let config_status = if config_path.exists() { "Exists" } else { "Not found" };
    
    let mut cmd = <Subcommand as clap::CommandFactory>::command();
    let help_text = format!(
        "\nFILES LOCATION:\n  Profile/Config: {} [{}]\n  Log file:       {} [{}]",
        config_path.display(), config_status,
        log_path.display(), log_status
    );
    cmd = cmd.after_help(help_text);
    
    let matches = cmd.get_matches();
    let subcommand = <Subcommand as clap::FromArgMatches>::from_arg_matches(&matches)
        .unwrap_or_else(|e| e.exit());

    subcommand.run().await
}
