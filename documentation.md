
# Documentation

## Installing Python 3.10 on RHEL 8

### Prerequisites
Before you begin, make sure you have sudo privileges on your system.

### Steps

1. **Install Required Packages**
    First, install the necessary packages for compiling Python from the source:

    ```bash
    sudo dnf install wget yum-utils make gcc openssl-devel bzip2-devel libffi-devel zlib-devel
    ```

2. **Download Python 3.10 Source Code**
    Download the source code for Python 3.10 from the official Python website:

    ```bash
    wget https://www.python.org/ftp/python/3.10.16/Python-3.10.16.tgz
    ```

3. **Extract the Archive**
    Extract the downloaded archive:

    ```bash
    tar xzf Python-3.10.16.tgz
    ```

4. **Prepare the Source Code**
    Navigate to the extracted directory and configure the source code:

    ```bash
    cd Python-3.10.16
    sudo ./configure --with-system-ffi --with-computed-gotos --enable-loadable-sqlite-extensions 
    ./configure --enable-optimizations
    ```

5. **Compile and Install**
    Compile and install Python 3.10:

    ```bash
    sudo make -j $(nproc)
    sudo make altinstall
    ```

6. **Verify the Installation**
    Check the installed Python version:

    ```bash
    python3.10 --version
    ```

7. **Update the Temporary PATH**
    Add the installation directory to your PATH:

    ```bash
    export PATH=/usr/local/bin:$PATH
    ```

    Verify the Python 3.10 installation again:

    ```bash
    python3.10 --version
    ```

8. **Make PATH Update Permanent**
    Update `.bashrc`:

    ```bash
    echo 'export PATH=/usr/local/bin:$PATH' >> ~/.bashrc
    source ~/.bashrc
    ```

9. **Verify the Installation Again**
    ```bash
    python3.10 --version
    ```

### Troubleshooting "command not found" Error for Python 3.10

1. **Verify Installation Path**
    Ensure that Python 3.10 is installed in the expected directory:

    ```bash
    sudo find / -name "python3.10"
    ```

    Example output:

    ```
    /usr/local/lib/python3.10
    /usr/local/include/python3.10
    /usr/local/bin/python3.10
    ```

2. **Temporarily Update the PATH**
    ```bash
    export PATH=/usr/local/bin:$PATH
    ```

    Verify the Python 3.10 Installation:

    ```bash
    python3.10 --version
    ```

## Installing Node.js 20 on RHEL 8.10

### Steps

1. **Enable the Node.js 20 Module**
    Enable the Node.js 20 module:

    ```bash
    sudo dnf module enable nodejs:20
    ```

2. **Install Node.js 20**
    Install Node.js 20 using dnf:

    ```bash
    sudo dnf install nodejs
    ```

3. **Verify the Installation**
    Check the installed Node.js version:

    ```bash
    node --version
    ```

    Example output:

    ```
    v20.18.2
    ```

## Installing PostgreSQL on RHEL 8

### Steps

1. **Add the PostgreSQL Repository**
    Add the PostgreSQL repository to your system:

    ```bash
    sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
    ```

2. **Disable the Default PostgreSQL Module**
    Disable the default PostgreSQL module to avoid conflicts:

    ```bash
    sudo dnf -qy module disable postgresql
    ```

3. **Install PostgreSQL 17**
    Install PostgreSQL 17 using dnf:

    ```bash
    sudo dnf install -y postgresql17-server
    ```

4. **Initialize the Database**
    Initialize the PostgreSQL database:

    ```bash
    sudo /usr/pgsql-17/bin/postgresql-17-setup initdb
    ```

5. **Enable and Start PostgreSQL Service**
    Enable and start the PostgreSQL service:

    ```bash
    sudo systemctl enable postgresql-17
    sudo systemctl start postgresql-17
    ```

6. **Verify the Installation**
    Check the installed PostgreSQL version:

    ```bash
    /usr/pgsql-17/bin/psql --version
    ```

## Installing Grafana on RHEL 8

### Steps

1. **Add the Grafana Repository**
    Add the Grafana repository to your system:

    ```bash
    sudo dnf install -y https://rpm.grafana.com/grafana-rpm-release-1.0.0-1.noarch.rpm
    ```

2. **Install Grafana**
    Install Grafana using dnf:

    ```bash
    sudo dnf install grafana
    ```

3. **Start and Enable Grafana Service**
    Start the Grafana service and enable it to start on boot:

    ```bash
    sudo systemctl start grafana-server
    sudo systemctl enable grafana-server
    ```

4. **Verify the Installation**
    Check the status of the Grafana service:

    ```bash
    sudo systemctl status grafana-server
    ```

## Installing VS Code on RHEL 8

### Steps

1. **Add the Microsoft Repository**
    Add the Microsoft repository for VSCode:

    ```bash
    sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
    ```

    Create the repository file:

    ```bash
    sudo sh -c 'echo -e "[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
type=rpm-md
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'
    ```

2. **Install VS Code**
    Install Visual Studio Code using dnf:

    ```bash
    sudo dnf install code
    ```

3. **Launch VSCode (Optional)**
    Launch VSCode:

    ```bash
    code
    ```

