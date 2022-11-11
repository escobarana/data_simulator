import sys
from confluent_kafka import Consumer, KafkaError, KafkaException, DeserializingConsumer
from confluent_kafka.schema_registry.json_schema import JSONDeserializer
from confluent_kafka.serialization import StringDeserializer
from telegrambot.kafkaconsumer.pc import Pc
from telegrambot.kafkaconsumer.raspberry import Raspberry
import os
from telegrambot.kafkaconsumer.schemas.pc_sensor_schema import schema as pc_schema
from telegrambot.kafkaconsumer.schemas.raspberry_sensor_schema import schema as rasp_schema

running = True


def dict_to_sensor_pc(obj, ctx):
    """
    Function to transform a dictionary object to a Pc object
    :param obj: dictionary to be transformed
    :param ctx:
    :return:
    """
    if obj is None:
        return None
    else:
        if 'TemperatureGPUCore' in obj and 'LoadGPUCore' in obj:
            return Pc(uuid=obj['uuid'],
                      device=obj['device'],
                      loading_datetime=obj['loading_datetime'],
                      ClockCPUCoreOne=obj['ClockCPUCoreOne'],
                      TemperatureCPUPackage=obj['TemperatureCPUPackage'],
                      LoadCPUTotal=obj['LoadCPUTotal'],
                      PowerCPUPackage=obj['PowerCPUPackage'],
                      TemperatureGPUCore=obj['TemperatureGPUCore'],
                      LoadGPUCore=obj['LoadGPUCore'])
        else:
            return Pc(uuid=obj['uuid'],
                      device=obj['device'],
                      loading_datetime=obj['loading_datetime'],
                      ClockCPUCoreOne=obj['ClockCPUCoreOne'],
                      TemperatureCPUPackage=obj['TemperatureCPUPackage'],
                      LoadCPUTotal=obj['LoadCPUTotal'],
                      PowerCPUPackage=obj['PowerCPUPackage'])


def dict_to_sensor_rasp(obj, ctx):
    """
    Function to transform a dictionary object to a Raspberry object
    :param obj: dictionary to be transformed
    :param ctx:
    :return:
    """
    if obj is None:
        return None
    return Raspberry(uuid=obj['uuid'],
                     device=obj['device'],
                     loading_datetime=obj['loading_datetime'],
                     gpu_temp_celsius=obj['gpu_temp_celsius'],
                     cpu_temp_celsius=obj['cpu_temp_celsius'],
                     frequency_arm_hz=obj['frequency_arm_hz'],
                     frequency_core_hz=obj['frequency_core_hz'],
                     frequency_pwm_hz=obj['frequency_pwm_hz'],
                     voltage_core_v=obj['voltage_core_v'],
                     voltage_sdram_c_v=obj['voltage_sdram_c_v'],
                     voltage_sdram_i_v=obj['voltage_sdram_i_v'],
                     voltage_sdram_p_v=obj['voltage_sdram_p_v'],
                     memory_arm_bytes=obj['memory_arm_bytes'],
                     memory_gpu_bytes=obj['memory_gpu_bytes'],
                     throttled=obj['throttled'])


# https://www.confluent.io/blog/getting-started-with-apache-kafka-in-python/?_ga=2.173179299.1203553419.1652971193-440072228.1652822793
class KafkaConsumer:
    """
    Class KafkaConsumer to consume data from kafkaproducer configuring the broker, schema registry
    and cloud settings from Confluent Cloud
    """

    def __init__(self):
        """
        Initialization of the class KafkaConsumer
        """
        conf = {'bootstrap.servers': os.environ["KAFKA_BROKER_SETTINGS"],
                'group.id': "foo",
                'auto.offset.reset': 'earliest'  # read from the beginning of the topic
                }

        if os.environ['TOPIC_NAME'] == 'PC':
            json_deserializer = JSONDeserializer(pc_schema, from_dict=dict_to_sensor_pc)
        else:
            json_deserializer = JSONDeserializer(rasp_schema, from_dict=dict_to_sensor_rasp)

        string_deserializer = StringDeserializer('utf_8')
        conf_schema = {
            'bootstrap.servers': os.environ["KAFKA_BROKER_SETTINGS"],
            'security.protocol': 'SASL_SSL',
            'sasl.mechanisms': 'PLAIN',
            'sasl.username': os.environ["KAFKA_CLUSTER_KEY"],
            'sasl.password': os.environ["KAFKA_CLUSTER_SECRET"],
            'key.deserializer': string_deserializer,
            'value.deserializer': json_deserializer,
            'group.id': 'json-consumer-group-1',
            'auto.offset.reset': 'earliest'  # read from the beginning of the topic
        }

        self.serializing_consumer = DeserializingConsumer(conf_schema)
        self.consumer = Consumer(conf)

    def consume(self, topics: list):
        """
        Function to consume data from a list of topics
        :param topics: list of topics to consume data from
        :return:
        """
        try:
            self.consumer.subscribe(topics)

            while running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition event
                        sys.stderr.write('%% %s [%d] reached end at offset %d\n' %
                                         (msg.topic(), msg.partition(), msg.offset()))
                    elif msg.error():
                        raise KafkaException(msg.error())
                else:
                    self.consumer.commit(asynchronous=False)
                    # msg_process(msg)

        finally:
            # Close down consumer to commit final offsets.
            self.consumer.close()

    def consume_json(self, topic_name: str):
        """
        Function to consume json documents from a kafkaproducer topic and print the information on screen
        :param topic_name: Name of the topic
        :return:
        """
        # https://docs.confluent.io/platform/current/installation/configuration/consumer-configs.html

        self.serializing_consumer.subscribe([topic_name])

        while True:
            try:
                msg = self.serializing_consumer.poll(1.0)
                if msg is None:
                    continue

                message = msg.value()
                if message is not None:
                    print(f'[\n'
                          f'\tNew measure: \n'
                          f'\tuuid: {message.uuid}\n'
                          f'\tdevice: {message.device}\n'
                          f'\tloading_datetime: {message.loading_datetime}\n')
            except KeyboardInterrupt:
                break

        print('Closing the Consumer ...')
        self.serializing_consumer.close()
