from dotenv import load_dotenv
from controller.speech import SpeechRecognitionController

def main():
    """
    Loads environment variables and triggers the main application logic 
    from the speech controller.
    """
    load_dotenv()
    # Create an instance of the controller
    controller = SpeechRecognitionController()
    # Call the start_listening method on the instance
    controller.start_listening()

if __name__ == "__main__":
    main()
