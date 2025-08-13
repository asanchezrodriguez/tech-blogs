1. git clone -b Chat-With-Data https://github.com/robrita/tech-blogs Chat-With-Data

2. copy sample.env to .env and update

3. python -m venv venv

4. .\venv\Scripts\activate (windows)
or source venv/bin/activate

5. python -m pip install -r requirements.txt

6. chainlit run app1.py

How to download azure cli?
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Download and install the Microsoft signing key
curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/

# Add the Azure CLI software repository
AZ_REPO=$(lsb_release -cs)
echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" | sudo tee /etc/apt/sources.list.d/azure-cli.list

# Update repository information and install the Azure CLI
sudo apt-get update
sudo apt-get install azure-cli
