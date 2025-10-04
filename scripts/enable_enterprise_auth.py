import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.auth.config_manager import security_config_manager

def enable_enterprise_features():
    """Loads security config, enables enterprise features, and saves it back."""
    print("Loading security configuration...")
    config = security_config_manager.load_config()

    print("Enabling Enterprise Authentication Features...")

    # Enable AD
    config["authentication"]["ad_enabled"] = True
    config["active_directory"]["configured"] = True
    print("- Active Directory enabled and marked as configured.")

    # Enable Okta
    config["authentication"]["okta_enabled"] = True
    config["okta"]["configured"] = True
    print("- Okta enabled and marked as configured.")

    # Enable MFA
    config["authentication"]["mfa_enabled"] = True
    config["mfa"]["configured"] = True
    # A specific MFA method must be enabled for it to be active
    config["mfa"]["totp_enabled"] = True
    print("- MFA enabled, marked as configured, and TOTP method is now active.")

    print("\nSaving updated security configuration...")
    success = security_config_manager.save_config(config, updated_by="system_script")

    if success:
        print("Configuration saved successfully.")
        print("\nPlease restart the application for the changes to take effect.")
    else:
        print("Error: Failed to save the configuration.")

if __name__ == "__main__":
    enable_enterprise_features()
