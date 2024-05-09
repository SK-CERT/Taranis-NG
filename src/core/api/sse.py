from flask_restful import Resource
import socket
import json
from flask import Response, stream_with_context, Flask
from flask import request, abort
from managers import auth_manager, bots_manager, time_manager, remote_manager


class TaranisSSE(Resource):
    @stream_with_context
    def stream(self):
        try:
            # Attempt to create a socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            print(f"Failed to create socket: {e}")
            return

        try:
            # Attempt to connect to the server

            sock.connect(('localhost', 5001))
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            sock.close()
            return

        buffer = ""
        try:
            while True:
                # Read byte by byte
                data = sock.recv(1)
                if data:
                    # Decode each byte received
                    char = data.decode('utf-8')
                    buffer += char
                    # Check if the character is the closing of a JSON object
                    if char == '}':
                        try:
                            # Try parsing the accumulated data
                            json_data = json.loads(buffer)
                            try:
                                yield f"event: {json_data['event']}\ndata: {json.dumps(json_data['data'])}\n\n"  # Yield the JSON data if successfully parsed
                            except Exception as e:
                                pass
                            buffer = ""  # Reset buffer after successful JSON parse
                        except json.JSONDecodeError:
                            # Continue accumulating data if JSON is not complete
                            continue
                else:
                    print("Connection closed by the server.")
                    break
        except Exception as e:
            print(f"Error during data reception or processing: {e}")
        finally:
            sock.close()

    def get(self):
        try:
            if request.args.get('jwt') is not None:
                if auth_manager.decode_user_from_jwt(request.args.get('jwt')) is None:
                    return "", 403
            elif request.args.get('api_key') is not None:
                if bots_manager.verify_api_key(request.args.get('api_key')) is False:
                    return "", 403
            else:
                return "", 403

            return Response(self.stream(), mimetype="text/event-stream")
        except Exception as e:
            return str(e), 500


def initialize(api):
    api.add_resource(TaranisSSE, "/sse")
