import time

from api.raspberrypi.raspberry import Raspberry
import os
import json
from dotenv import load_dotenv

from kafka.producer import KafkaProducer


def write_local(data, filename='sample.json'):
    """
        This function writes in a json file locally the Raspberry Pi data for testing purposes
    :param data: The new data measures from the device to be added to the file
    :param filename: The name of the ile to write to, by default 'sample.json'
    :return: None
    """
    with open(filename, 'r+') as file:
        # First we load existing data into a dict
        file_data = json.load(file)
        # Join data with file_data inside raspberry
        file_data["raspberry"].append(data)
        # Set file's current position at offset
        file.seek(0)
        # Convert back to json
        json.dump(file_data, file, indent=4)


def data_push():
    """
        This function sends a json message to the Kafka topic specified from the Raspberry Pi device
    :return: None
    """
    # Loads the environmental variables within the .env file
    load_dotenv()
    topic = os.environ['TOPIC_NAME_IOT']
    raspberry = Raspberry().json
    print('\n --------- ')
    print(raspberry['uuid'])
    print('\n --------- ')
    KafkaProducer().produce_json(topic_name=topic, data=raspberry)
    # write_local(raspberry)


if __name__ == "__main__":
    while True:
        data_push()
        time.sleep(5)  # Every 5 seconds to avoid data repetition in small periods of time
