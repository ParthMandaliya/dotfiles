#!/bin/bash

if command -v dnf &> /dev/null; then
    PKGMGR="dnf"
elif command -v apt &> /dev/null; then
    PKGMGR="apt"
else
    echo "No supported package manager found (dnf or apt). Exiting..."
    exit 1
fi


function update_repositories() {
    if [ "$PKGMGR" = "apt" ]; then
        apt update
    fi
}

function is_package_installed() {
    command -v "$1" &> /dev/null
}


# Install fzf
echo "Installing fzf..."
update_repositories
$PKGMGR install -y fzf

# Install starship
if ! is_package_installed starship; then
    # Install wget, zip and unzip 
    echo "Installing dependencies packages..."
    update_repositories
    $PKGMGR install -y wget zip unzip

    # Install Starship dependency fonts
    echo "Installing Starship dependency fonts..."
    wget https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/FiraCode.zip -O /tmp/FiraCode.zip
    mkdir -p "$HOME/.fonts/FiraCode"
    unzip /tmp/FiraCode.zip -d "$HOME/.fonts/FiraCode"
    rm /tmp/FiraCode.zip

    # Install curl
    echo "Installing curl..."
    update_repositories
    $PKGMGR install -y curl
    
    # Install starship
    echo "Installing Starship, please follow the instructions on the terminal to complete the installation..."
    curl -sS https://starship.rs/install.sh | sh
    mkdir -p "$HOME/.config"
    ln -s "$(pwd)/starship.toml" "$HOME/.config/starship.toml"
fi

# Install vim
echo "Installing Vim..."
update_repositories
$PKGMGR install -y vim
if [ -f "$HOME/.vimrc" ]; then
    mv "$HOME/.vimrc" "$HOME/.vimrc.bak"
    echo "Existing .vimrc backed up to .vimrc.bak"
fi
ln -s "$(pwd)/.vimrc" "$HOME/.vimrc"
echo "Vim installed and .vimrc linked successfully."

# TODO: install com.mattjakeman.ExtensionManager using flatpak, if flatpak is not installed, 
# prompt user to install flatpak manually and then install com.mattjakeman.ExtensionManager using flatpak

# TODO: backup $HOME/.local/share/gnome-shell/extensions and
# symlink $(pwd)/extensions/local to $HOME/.local/share/gnome-shell/extensions

# TODO: install gnome-shell-extension-appindicator gnome-shell-extension-dash-to-dock package using package manager
# backup /usr/share/gnome-shell/extensions/{appindicatorsupport@rgcjonas.gmail.com,dash-to-dock@micxgx.gmail.com}
# and symlink $(pwd)/extensions/system/{appindicatorsupport@rgcjonas.gmail.com,dash-to-dock@micxgx.gmail.com} 
# to /usr/share/gnome-shell/extensions/
# prompt user to logout and login again and enable extensions in extension manager 

# Put bashrc in place
if [ -f "$HOME/.bashrc" ]; then
    mv "$HOME/.bashrc" "$HOME/.bashrc.bak"
    echo "Existing .bashrc backed up to .bashrc.bak"
fi
ln -s "$(pwd)/.bashrc" "$HOME/.bashrc"
echo ".bashrc linked successfully."
