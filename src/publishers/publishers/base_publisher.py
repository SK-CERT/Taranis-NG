from taranisng.schema.publisher import PublisherSchema


class BasePublisher:
    type = "BASE_PUBLISHER"
    name = "Base Publisher"
    description = "Base abstract type for all publishers"

    parameters = []

    def get_info(self):
        info_schema = PublisherSchema()
        return info_schema.dump(self)

    def publish(self, publisher_input):
        pass

    def print_exception(self, error):
        publisher_info = BasePublisher.get_info(self)
        print('Publisher ID: ' + publisher_info['id'])
        print('Publisher name: ' + publisher_info['name'])
        if str(error).startswith('b'):
            print('ERROR: ' + str(error)[2:-1])
        else:
            print('ERROR: ' + str(error))
