from dotenv import load_dotenv
from controller import speech

def main():
    """
    Loads environment variables and triggers the main application logic 
    from the speech controller.
    """
    load_dotenv()
    speech.start_listening()

if __name__ == "__main__":
    main()
