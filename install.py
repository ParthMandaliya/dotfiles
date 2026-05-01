from dataclasses import dataclass
from subprocess import run, PIPE
import warnings
import shutil
import os


@dataclass
class PkgMgr:
    apt: str = "apt"
    dnf: str = "dnf"

@dataclass
class Shell:
    bash: str = "bash"
    zsh: str = "zsh"
    fish: str = "fish"


def detect_package_manager():
    """
    Detects the system's primary package manager by checking available executables.
    """
    if is_package_installed("apt"):
        return PkgMgr.apt
    elif is_package_installed("dnf"):
        return PkgMgr.dnf
    else:
        raise EnvironmentError("No supported package manager found (apt or dnf).")

def detect_shell():
    """
    Detects the user's default shell.
    """
    with open(f"/proc/{os.getppid()}/comm", "r") as f:
        shell_name = f.read().strip()
    if shell_name not in (Shell.bash, Shell.zsh, Shell.fish):
        raise EnvironmentError("No supported shell found (bash, zsh, or fish).")
    return shell_name

def is_package_installed(package_name: str):
    """
    Checks if a package is installed on the system.
    """
    return shutil.which(package_name) is not None

def update_repositories(pkgmgr: str):
    """
    Updates the apt repositories if the detected package manager is apt.
    """
    if pkgmgr == PkgMgr.apt:
        run(["apt", "update"], check=True, shell=False)

def install_package(pkgmgr: str, package_name: str):
    """
    Installs a package using the specified package manager.
    """
    if pkgmgr == PkgMgr.apt:
        run(["apt", "install", "-y", package_name], check=True, shell=False)
    elif pkgmgr == PkgMgr.dnf:
        run(["dnf", "install", "-y", package_name], check=True, shell=False)

def run_command(command: str, shell: bool = False, stdout=PIPE):
    """
    Runs a shell command and checks for errors.
    """
    run(command, check=True, stdout=stdout, shell=shell)


if __name__ == "__main__":
    pkgmgr = detect_package_manager()
    print(f"Detected package manager: {pkgmgr}")

    update_repositories(pkgmgr)

    # installing wget
    print("Installing wget...")
    install_package(pkgmgr, "wget")

    # installing fzf
    print("Installing fzf...")
    install_package(pkgmgr, "fzf")
    
    # check fzf version
    fzf_version = run(
        "fzf --version | awk '{print $1}'",
        check=True, stdout=PIPE, shell=True
    ).stdout.decode().strip()
    print(f"Installed fzf version: {fzf_version}")

    shell = detect_shell()
    # backup .{shell}rc
    if os.path.exists(f"{os.getenv('HOME')}/.{shell}rc"):
        run_command(f"cp {os.getenv('HOME')}/.{shell}rc {os.getenv('HOME')}/.{shell}rc.bak", shell=True)

    run_command(f"mkdir -p {os.getenv('HOME')}/.config", shell=True)        
    if fzf_version < "0.48.0":
        completion_url = f"https://raw.githubusercontent.com/junegunn/fzf/refs/tags/{fzf_version}/shell/completion.{shell}"
        key_bindings_url = f"https://raw.githubusercontent.com/junegunn/fzf/refs/tags/{fzf_version}/shell/key-bindings.{shell}"

        run_command(f"mkdir -p {os.getenv('HOME')}/.config/fzf", shell=True)        
        if shell == Shell.fish:
            run_command(
                f"wget {completion_url} -O {os.getenv('HOME')}/.config/fzf/ ",
                shell=True
            )
            with open(f"{os.getenv('HOME')}/.{shell}rc", "a") as shellrc:
                shellrc.write("\n\n# fzf configuration\n")
                shellrc.write(f"source {os.getenv('HOME')}/.config/fzf/completion.{shell}\n")
        else:
            run_command(
                f"wget {completion_url} -O {os.getenv('HOME')}/.config/fzf/completion.{shell}",
                shell=True
            )
            run_command(
                f"wget {key_bindings_url} -O {os.getenv('HOME')}/.config/fzf/key-bindings.{shell}",
                shell=True
            )
            with open(f"{os.getenv('HOME')}/.{shell}rc", "a") as shellrc:
                shellrc.write("\n# fzf configuration\n")
                shellrc.write(f"source {os.getenv('HOME')}/.config/fzf/completion.{shell}\n")
                shellrc.write(f"source {os.getenv('HOME')}/.config/fzf/key-bindings.{shell}\n")
    else:
        with open(f"{os.getenv('HOME')}/.{shell}rc", "a") as shellrc:
            shellrc.write("\n# fzf configuration\n")
            shellrc.write(f'eval "$(fzf --$(echo $SHELL | cut -d"/" -f3))"\n')
            # shellrc.write(f'eval "$(fzf --{shell})"\n')

    print(f"fzf configuration added to {os.getenv('HOME')}/.{shell}rc")

    # installing starship
    print("Installing starship dependencies packages...")
    install_package(pkgmgr, "zip")
    install_package(pkgmgr, "unzip")
    install_package(pkgmgr, "curl")


    print("Installing firacode fonts...")
    run_command(
        "wget https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/FiraCode.zip -O /tmp/FiraCode.zip",
        shell=True
    )
    run_command(f"mkdir -p {os.getenv('HOME')}/.fonts/FiraCode", shell=True)
    run_command(f"unzip -o /tmp/FiraCode.zip -d {os.getenv('HOME')}/.fonts/FiraCode", shell=True)
    run_command("rm /tmp/FiraCode.zip", shell=True)

    print("Installing Starship, please follow the instructions on the terminal to complete the installation...")
    run_command("curl -sS https://starship.rs/install.sh | sh", shell=True, stdout=None)
    run_command(f"ln -s $(pwd)/starship.toml {os.getenv('HOME')}/.config/starship.toml", shell=True)
    with open(f"{os.getenv('HOME')}/.{shell}rc", "a") as shellrc:
        shellrc.write("\n# Starship configuration\n")
        shellrc.write(f'eval "$(starship init $(echo $SHELL | cut -d"/" -f3))"\n')
        # shellrc.write(f'eval "$(starship init {shell})"\n')
        # shellrc.write(f'eval "$(starship init $SHELL)"\n')

    # installing vim
    print("Installing vim...")
    install_package(pkgmgr, "vim")
    if os.path.exists(f"{os.getenv('HOME')}/.vimrc"):
        run_command(f"cp {os.getenv('HOME')}/.vimrc {os.getenv('HOME')}/.vimrc.bak", shell=True)
    run_command(f"ln -s $(pwd)/.vimrc {os.getenv('HOME')}/.vimrc", shell=True)

    # custom aliases
    with open(f"{os.getenv('HOME')}/.{shell}rc", "a") as shellrc:
        shellrc.write("\n# Custom aliases\n")
        shellrc.write("alias ll='ls -alF'\n")
        shellrc.write("alias la='ls -A'\n")
        shellrc.write("alias l='ls -CF'\n")
        shellrc.write("alias c=clear\n")

    # TODO: install com.mattjakeman.ExtensionManager using flatpak, if flatpak is not installed, 
    # prompt user to install flatpak manually and then install com.mattjakeman.ExtensionManager using flatpak
    if not is_package_installed("flatpak"):
        warnings.warn(
            "Flatpak is not installed. Please install and configure Flatpak manually and "
            "install com.mattjakeman.ExtensionManager using Flatpak to manage your shell extensions."
        )

    # backup $HOME/.local/share/gnome-shell/extensions
    os.makedirs(f"{os.getenv('HOME')}/.local/share/gnome-shell/extensions", exist_ok=True)
    run_command((
        f"mv {os.getenv('HOME')}/.local/share/gnome-shell/extensions "
        f"{os.getenv('HOME')}/.local/share/gnome-shell/extensions.bak"
    ), shell=True)

    run_command((
        "ln -s "
        "$(pwd)/extensions/local "
        f"{os.getenv('HOME')}/.local/share/gnome-shell/extensions"
    ), shell=True)

    if not is_package_installed("gnome-shell-extension-appindicator"):
        install_package(pkgmgr, "gnome-shell-extension-appindicator")
    if not is_package_installed("gnome-shell-extension-dash-to-dock"):
        install_package(pkgmgr, "gnome-shell-extension-dash-to-dock")
    
    run_command("sudo mkdir -p /usr/share/gnome-shell/extensions/", shell=True)
    if os.path.exists("/usr/share/gnome-shell/extensions/appindicatorsupport@rgcjonas.gmail.com"):
        run_command((
            "sudo mv "
            "/usr/share/gnome-shell/extensions/appindicatorsupport@rgcjonas.gmail.com "
            "/usr/share/gnome-shell/extensions/appindicatorsupport@rgcjonas.gmail.com.bak"
        ), shell=True)
    elif os.path.exists("/usr/share/gnome-shell/extensions/dash-to-dock@micxgx.gmail.com"):
        run_command((
            "sudo mv "
            "/usr/share/gnome-shell/extensions/dash-to-dock@micxgx.gmail.com "
            "/usr/share/gnome-shell/extensions/dash-to-dock@micxgx.gmail.com.bak"
        ), shell=True)
        run_command((
            "sudo ln -s "
            "$(pwd)/extensions/system/appindicatorsupport@rgcjonas.gmail.com "
            "/usr/share/gnome-shell/extensions/"
        ), shell=True)
        run_command((
            "sudo ln -s "
            "$(pwd)/extensions/system/dash-to-dock@micxgx.gmail.com "
            "/usr/share/gnome-shell/extensions/"
        ), shell=True)
    print("Gnome shell extensions configured. Please log out and log back in to see the changes.")
