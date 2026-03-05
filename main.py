from saving.userfiles import save_response_u, save_response_sv, save_response_svu
from login.processor import login_processor

from dotenv import load_dotenv
import os
load_dotenv()

serviceip = os.getenv("host")

def tree():
    choice = input("Would you like to 1) Create or 2) Login: ").strip()

    if choice == "1":
        create = input("Which save function to run? (u/sv/svu): ").strip().lower()
        if create == "u":
            save_response_u()
            tree()
        elif create == "sv":
            save_response_sv()
            tree()
        elif create == "svu":
            save_response_svu()
            tree()
        else:
            print("Invalid choice, please try again.")
            tree()

    elif choice == "2":
        sv_uuid = input("What is the service UUID to login to?: ").strip()
        if sv_uuid == "":
            print("Service UUID cannot be empty.")
            tree()
            return
        svu_uuid = input("What is the account UUID to login to?: ").strip()
        if svu_uuid == "":
            print("Account UUID cannot be empty.")
            tree()
            return

        login_processor(sv_uuid, svu_uuid, serviceip)
        tree()

    else:
        print("Invalid choice, please try again.")
        tree()


if __name__ == "__main__":
    tree()
