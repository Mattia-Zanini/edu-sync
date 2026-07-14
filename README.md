# Edu Sync

Edu Sync is a command line application that synchronizes the contents of Moodle instances to your computer.

It accesses the Moodle instance via the Moodle mobile web services API, which is also used by the official Moodle mobile app.
To be able to use Edu Sync with a Moodle instance, the Moodle mobile web services must explicitly be enabled by the instance.

This application is written in Rust with a focus on speed.
Downloads are performed concurrently, which is beneficial when syncing many small files.

## Usage

You can view more detailed help information with:

```bash
$ edu-sync-cli help
```

### Account Management

Edu Sync provides several commands to manage your Moodle accounts (profiles) directly from the terminal.

#### 1. Add an account (`add`)
Connects to the Moodle server, fetches your user info, and saves the configuration.

*   **Using username and password:**
    ```bash
    $ edu-sync-cli add --username <username> https://example.com ~/download-dir
    # You will be prompted to enter your password
    ```

*   **Using a token:**
    If your instance uses SSO (Single Sign-On) or you want to use a token directly, run:
    ```bash
    $ edu-sync-cli add https://example.com ~/download-dir
    # You will be prompted to enter your token
    ```
    *See [TOKEN_GUIDE.md](TOKEN_GUIDE.md) for instructions on how to obtain it.*

#### 2. List accounts (`list`)
Displays all currently configured accounts along with their IDs and Moodle URLs.
```bash
$ edu-sync-cli list
```

#### 3. Update an account (`update`)
Allows you to update the credentials (e.g., when an SSO token expires) or change the target download directory of an existing account. The command always asks you interactively which account you want to update.

You can update your account in three different ways:

*   **Update ONLY the Token:**
    Run the update command without arguments. You will be prompted to paste your new token.
    ```bash
    $ edu-sync-cli update
    ```
    *(You can optionally supply `--username <username>` if you wish to re-authenticate with a password instead of a token).*

*   **Update ONLY the Download Path:**
    Pass the `--path` argument. When prompted for a new token, simply press **Enter** to leave it empty and keep your current token.
    ```bash
    $ edu-sync-cli update --path /new/download-dir
    ```

#### 4. Remove an account (`remove`)
Opens an interactive menu to let you safely delete an account from the configuration.
```bash
$ edu-sync-cli remove
```

### Syncing Courses

Once your accounts are set up, you can manage the synchronization of your courses.

#### 1. Fetch available courses (`fetch`)
Queries the Moodle server for all courses you are enrolled in and populates the config file with them.
```bash
$ edu-sync-cli fetch
```

#### 2. Configure courses to sync (`config`)
By default, courses are not downloaded automatically. You must enable synchronization for the specific courses you want.

1. Find the path to your configuration file by running:
   ```bash
   $ edu-sync-cli config
   ```
2. Open the returned `.toml` file in any text editor.
3. Locate the `[accounts.YOUR_ACCOUNT_ID.courses]` section.
4. Under the name of the course you wish to download, change `sync = false` to `sync = true`.

*Note: The TOML file acts as the "single source of truth". You can also manually remove accounts or change paths by editing this file directly.*

#### 3. Perform the Sync (`sync`)
Downloads all resources from the courses that have `sync = true` in your configuration.
```bash
$ edu-sync-cli sync
```

## Installation

The binary name for Edu Sync is `edu-sync-cli`.

Since this is a fork, precompiled binaries are not provided. You can compile and install the application directly from the source code using Cargo (Rust's package manager). 

To do so, run the following command from the root of the repository:

```bash
cargo install --path edu-sync-cli
```

This command compiles the project and installs the executable into your `~/.cargo/bin` directory. This is necessary because it makes the `edu-sync-cli` command available globally in your terminal, allowing you to run it from anywhere without needing to specify the full path to the executable.

### Shell completions

Edu Sync uses clap's dynamic completions. To generate the completion stub, use:

```sh
COMPLETE=<SHELL> edu-sync-cli
```

Where `<SHELL>` is one of `bash`, `elvish`, `fish`, `powershell` or `zsh`

## Moodle Cleanup Script

The project includes a Python utility script, [`cleanup_moodle.py`](cleanup_moodle.py), designed to organize and clean up the files and directories downloaded by Edu Sync.

### Purpose
When Edu Sync downloads files from Moodle, they often contain numerical Moodle IDs, invalid characters, or are nested in redundant folders. This script cleans the folder structure to make it more human-readable and accessible.

### Result / What it does
1. **Removes Moodle IDs:** Strips the numerical ID prefixes from file and directory names.
2. **Converts HTML Links:** Automatically identifies `.html` files that are simply Moodle redirects/links, extracts the target URL, and converts the file to a plain `.txt` file containing the link.
3. **Sanitizes Names:** Removes invalid characters (`< > : " / \ | ? *`) to ensure native compatibility across Windows, macOS, and Linux.
4. **Flattens Directories:** If a directory contains only a single item (one file or subfolder), the script moves that item up one level and deletes the empty directory.
5. **Smart Conflict Resolution:** If two files end up with the same name after cleaning, the script intelligently appends the original Moodle ID (or a numeric counter) to prevent overwriting.

> [!WARNING]
> While using this script is highly recommended for achieving a much cleaner and more readable organization of your downloaded courses, **it will compromise future synchronization**.
> Because the script actively modifies file names, folder names, and their overall structure, Edu Sync will no longer recognize the previously downloaded files. Running `edu-sync-cli sync` again on the same directory will cause it to re-download the original files from Moodle alongside your cleaned ones.

### Usage
Run the script passing the path to your downloaded Moodle folder as an argument:
```bash
python3 cleanup_moodle.py ~/download-dir
```

## Licensing

This project is licensed under
* The GNU General Public License v3.0 only ([LICENSE](LICENSE), or https://www.gnu.org/licenses/gpl-3.0.html)

### Trademark Notice

Moodle™ is a [registered trademark](https://moodle.com/trademarks/) of Moodle Pty Ltd in many countries. Edu Sync is not sponsored, endorsed, licensed by, or affiliated with Moodle Pty Ltd.
