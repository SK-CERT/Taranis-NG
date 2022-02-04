from keycloak import KeycloakAdmin
import click

@click.command()
@click.argument('url', default='http://keycloak.local')
@click.argument('user', default='admin')
@click.argument('password', default='supersecret')
@click.argument('admin-realm', default='master')
@click.argument('realm', default='taranis')
@click.argument('verify', default=False)
def main(url, user, password, admin_realm, realm, verify):
    server_url = "{}/auth/".format(url)
    keycloak_admin = KeycloakAdmin(server_url=server_url,
                               username=user,
                               password=password,
                               realm_name=admin_realm,
                               # client_secret_key="client-secret",
                               verify=verify)

    print(keycloak_admin.create_realm(payload={"realm": realm}, skip_exists=True))


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