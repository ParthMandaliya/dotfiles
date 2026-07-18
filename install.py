from enum import Enum
from pathlib import Path
from subprocess import run, PIPE
import os
import shutil


class PackageManager(str, Enum):
    APT = "apt"
    DNF = "dnf"


class Shell(str, Enum):
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"


HOME = Path.home()
DOTFILES_DIR = Path(__file__).parent


def detect_package_manager() -> PackageManager:
    for mgr in PackageManager:
        if shutil.which(mgr.value):
            return mgr
    raise EnvironmentError("No supported package manager found (apt or dnf).")


def detect_shell() -> Shell:
    shell_name = Path(os.environ.get("SHELL", "")).name
    try:
        return Shell(shell_name)
    except ValueError:
        raise EnvironmentError(
            f"Unsupported shell: {shell_name!r}. Supported: {[s.value for s in Shell]}"
        )


def update_repositories(pkgmgr: PackageManager) -> None:
    if pkgmgr == PackageManager.APT:
        run(["sudo", "apt", "update"], check=True)


def install_package(pkgmgr: PackageManager, *packages: str) -> None:
    if pkgmgr == PackageManager.APT:
        run(["sudo", "apt", "install", "-y", *packages], check=True)
    elif pkgmgr == PackageManager.DNF:
        run(["sudo", "dnf", "install", "-y", *packages], check=True)


def clone_repo(
        repo_url: str,
        destination: Path | None = None,
        checkout: str | None = None
    ) -> Path:
    repo_name = Path(repo_url.rstrip("/"))
    if repo_name.suffix == ".git":
        repo_name = repo_name.with_suffix("")
    repo_name = Path(repo_name.name)

    if destination is None:
        destination = HOME / repo_name

    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")

    run(["git", "clone", repo_url, str(destination)], check=True)

    if checkout is not None:
        # checkout can be a branch, tag, or commit id
        run(["git", "-C", str(destination), "checkout", checkout], check=True)

    return destination


def is_installed(name: str) -> bool:
    return shutil.which(name) is not None


# Untested code
def backup(path: Path) -> None:
    if path.exists() or path.is_symlink():
        backup_path = path.parent / (path.name + ".bak")
        if path.is_dir() and not path.is_symlink():
            shutil.copytree(path, backup_path)
        else:
            shutil.copy2(path, backup_path, follow_symlinks=True)


def symlink(src: Path, dst: Path) -> None:
    backup(dst)
    dst.symlink_to(src)


def append_to_shellrc(shell: Shell, *lines: str) -> None:
    shellrc = HOME / f".{shell.value}rc"
    with open(shellrc, "a") as f:
        f.write("\n")
        f.writelines(line + "\n" for line in lines)


def install_fzf(pkgmgr: PackageManager, shell: Shell) -> None:
    print("Installing fzf...")
    install_package(pkgmgr, "fzf")

    version_str = run(
        ["fzf", "--version"], check=True, stdout=PIPE, text=True
    ).stdout.split()[0]

    # Parse into a tuple for correct semantic version comparison.
    # String comparison fails: "0.9.0" > "0.48.0" lexicographically but 0.9.0 < 0.48.0 semantically.
    version = tuple(int(x) for x in version_str.split("."))

    if version >= (0, 48, 0):
        append_to_shellrc(shell,
            "# fzf",
            'eval "$(fzf --$(basename $SHELL))"',
        )
    else:
        _configure_fzf_legacy(shell, version_str)

    print(f"fzf {version_str} configured.")


def _configure_fzf_legacy(shell: Shell, version: str) -> None:
    fzf_dir = HOME / ".config" / "fzf"
    fzf_dir.mkdir(parents=True, exist_ok=True)

    base = f"https://raw.githubusercontent.com/junegunn/fzf/refs/tags/{version}/shell"
    completion = fzf_dir / f"completion.{shell.value}"

    run(["wget", f"{base}/completion.{shell.value}", "-O", str(completion)], check=True)
    lines = ["# fzf", f"source {completion}"]

    if shell != Shell.FISH:
        key_bindings = fzf_dir / f"key-bindings.{shell.value}"
        run(["wget", f"{base}/key-bindings.{shell.value}", "-O", str(key_bindings)], check=True)
        lines.append(f"source {key_bindings}")

    append_to_shellrc(shell, *lines)


def install_starship(pkgmgr: PackageManager, shell: Shell) -> None:
    print("Installing starship dependencies...")
    install_package(pkgmgr, "zip", "unzip", "curl", "wget")

    print("Installing FiraCode Nerd Font...")
    fonts_dir = HOME / ".fonts" / "FiraCode"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    firacode_zip = Path("/tmp/FiraCode.zip")
    run(
        ["wget", "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/FiraCode.zip",
         "-O", str(firacode_zip)],
        check=True,
    )
    run(["unzip", "-o", str(firacode_zip), "-d", str(fonts_dir)], check=True)
    firacode_zip.unlink()

    print("Installing starship (follow any prompts)...")
    run("curl -sS https://starship.rs/install.sh | sh", shell=True, check=True)

    config_dir = HOME / ".config"
    config_dir.mkdir(exist_ok=True)
    symlink(DOTFILES_DIR / "starship.toml", config_dir / "starship.toml")

    append_to_shellrc(shell,
        "# starship",
        'eval "$(starship init $(basename $SHELL))"',
    )
    print("Starship configured.")


def install_vim(pkgmgr: PackageManager) -> None:
    print("Installing vim...")
    install_package(pkgmgr, "vim")
    symlink(DOTFILES_DIR / ".vimrc", HOME / ".vimrc")
    print("vim configured.")


def configure_aliases(shell: Shell) -> None:
    append_to_shellrc(shell,
        "# aliases",
        "alias ll='ls -alF'",
        "alias la='ls -A'",
        "alias l='ls -CF'",
        "alias c=clear",
    )


def main() -> None:
    pkgmgr = detect_package_manager()
    print(f"Package manager: {pkgmgr.value}")

    shell = detect_shell()
    print(f"Shell: {shell.value}")

    shellrc = HOME / f".{shell.value}rc"
    backup(shellrc)
    shellrc.touch(exist_ok=True)

    update_repositories(pkgmgr)

    install_fzf(pkgmgr, shell)
    install_starship(pkgmgr, shell)
    install_vim(pkgmgr)
    configure_aliases(shell)

    # Untested code
    resp = input("Do you want to continue with installing GNOME extension (y/n)?").lower()
    while resp not in ("y", "yes", "n", "no"):
        print("Invalid response...")
    if resp in ("n", "no"):
        import sys
        sys.exit(0)

    install_package(pkgmgr, "make")
    dest = clone_repo(
        "https://github.com/icedman/search-light.git",
        checkout="4e93e0e3e2fba8512dfd588177b7a6a2a71c9f1e"
    )
    run(["cd", f"{str(dest)}", "&&", "make"], check=True)
    print("Installed search light")
    
    install_package(pkgmgr, "gnome-shell-extension-appindicator")
    print("Installed appindicator extension")
    
    install_package(pkgmgr, "gnome-shell-extension-dash-to-dock")
    print("Installed dash-to-dock")  

    # TODO:
    # Add the code to copy extensions available with this repo 
    # to right places
    # extensions/local -> ~/.local/share/gnome-shell/extensions/
    # extensions/system -> /usr/share/gnome-shell/extensions/ 
    # Ask user to install flatpak and via flatpak, install com.mattjakeman.ExtensionManager
    # if not already installed. From extension manager user can manage extensions 

    # TODO:
    # Modidy the following files, and add the new code, new code
    #  will handle the lid-close action
    # 
    # sudo mkdir -p /etc/systemd/logind.conf.d
    # sudo tee /etc/systemd/logind.conf.d/lid-switch.conf << 'EOF'
    # [Login]
    # HandleLidSwitch=ignore
    # HandleLidSwitchExternalPower=ignore
    # HandleLidSwitchDocked=ignore
    # EOF
    # sudo systemctl restart systemd-logind

    # TODO:
    # loginctl enable-linger $USER
    # don't let systemd stop when logged out, otherwise plex.container and 
    # tailscale.container will stop too
    # 
    # sudo firewall-cmd --permanent --add-port=32400/tcp
    # enables the 32400 port for plex permanently (not necessary if using tailscale)
    # sudo firewall-cmd --reload
    # reload the firewall to apply changes
    # 
    # gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 0
    # gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0
    # do not let laptop go to sleep or suspension ever
    # 
    # sudo -U gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 0
    # sudo -U gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0
    # if user never has logged in (fresh reboot for example) laptop will go to 
    # sleep/suspension after sometime (no user logged in; root settings apply, this changes
    # root settings)

    # TODO:
    # After adding the above code, re-write the below statements.
    
    print()
    print("Logout and log back in for extension to take effect.")
    print()
    print("Please install Flatpak and then use it to install com.mattjakeman.ExtensionManager.")
    print("Afterward, install the Clipboard Indicator extension by Tudmotu through the Extension Manager.")
    print()
    print("You can use the extension manager to configure the behaviour and appearance of newly installed extensions.")

    print(f"\nDone. Logout and back in to see the new font in action.")
    print("Enjoy your new setup!")


if __name__ == "__main__":
    main()
