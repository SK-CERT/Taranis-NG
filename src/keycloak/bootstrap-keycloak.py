from keycloak import KeycloakAdmin
import click

@click.command()
@click.argument('url', default='http://keycloak.local')
@click.argument('user', default='admin')
@click.argument('password', default='supersecret')
@click.argument('realm', default='master')
@click.argument('verify', default=False)
def main(url, user, password, realm, verify):
    server_url = "{}/auth/".format(url)
    keycloak_admin = KeycloakAdmin(server_url=server_url,
                               username=user,
                               password=password,
                               realm_name=realm,
                               # client_secret_key="client-secret",
                               verify=verify)

    keycloak_admin.create_client(payload={"enabled": True, "clientId": "taranis"}, skip_exists=True)
    print(keycloak_admin.get_clients())


# Add user and set password
    # new_user = keycloak_admin.create_user({"email": "example@example.com",
    #                 "username": "example@example.com",
    #                 "enabled": True,
    #                 "firstName": "Example",
    #                 "lastName": "Example",
    #                 "credentials": [{"value": "secret","type": "password",}]})

# Create a new Realm


if __name__ == '__main__':
    main(auto_envvar_prefix='TARANIS_KEYCLOAK')