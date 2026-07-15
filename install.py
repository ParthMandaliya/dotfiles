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


def is_installed(name: str) -> bool:
    return shutil.which(name) is not None


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

    # TODO:
    # ask user if they want to install extension?
    # if yes:
    #   install make
    #   clone https://github.com/icedman/search-light.git
    #   checkout to 4e93e0e3e2fba8512dfd588177b7a6a2a71c9f1e
    #   cd search-light
    #   make
    # install gnome-shell-extension-appindicator gnome-shell-extension-dash-to-dock
    # inform user to install flatpak and com.mattjakeman.ExtensionManager
    # and configure the extensions however they like


    print(f"\nDone. Logout and back in to see the new font in action.")
    print("Enjoy your new setup!")


if __name__ == "__main__":
    main()
