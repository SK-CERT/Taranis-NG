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
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            print(f"Failed to create socket: {e}")
            return

        try:
            sock.connect(('localhost', 5001))
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            sock.close()
            return

        buffer = ""
        try:
            while True:
                data = sock.recv(1)
                if not data:
                    break

                char = data.decode('utf-8')
                buffer += char

                if char == '}':
                    try:
                        json_data = json.loads(buffer)
                    except json.JSONDecodeError:
                        continue

                    yield f"event: {json_data['event']}\ndata: {json.dumps(json_data['data'])}\n\n"
                    buffer = ""

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
