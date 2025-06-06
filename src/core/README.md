# **Taranis NG backend setup**
1. Install **Postgresql** database and create database e.g. taranisdb
2. Install **Python 3.13** or later
3. In taranis-ng-common, taranis-ng-collectors and taranis-ng-core install and activate python virtual environment:
    `virtualenv -p python3.7 venv`
    `source venv/bin/activate`
    `pip3 install -r requirements.txt`
4. Set environment variables for taranis-ng-core:
    DB_URL=127.0.0.1:5432;DB_DATABASE=taranisdb;DB_USER=<YOUR-DB-USER>
5. Set secrets (passwords) for taranis-ng-core:
    api_key.txt, jwt_secret_key.txt, postgres_password.txt
6. Before first run uncomment line with `import test.py` in app.py to create set of test data. After first run comment this line again.
7. Run taranis-ng-core: `python3 run.py`
8. Set environment variables for taranis-ng-collectors:
    FLASK_RUN_PORT=5001;API_KEY=12345;TARANIS_NG_CORE_URL=http://127.0.0.1:5000;SSL_VERIFICATION=False
9. Run taranis-ng-collectors: `python3 run.py` and it should collect first set of RSS news items from preconfigured test osint source

# **Taranis NG frontend setup**
1. Install Node.js from https://nodejs.org/en/
1. Set environment variables for taranis-ng-gui:
    VUE_APP_TARANIS_NG_URL=http://127.0.0.1:8080;VUE_APP_TARANIS_NG_CORE_API=http://127.0.0.1:5000/api;VUE_APP_TARANIS_NG_LOCALE=en;VUE_APP_TARANIS_NG_CORE_SSE=http://127.0.0.1:5000/sse
3. Install all required packages: `npm install`
4. Run application inside taranis-ng-gui: `npm run serve`
5. In Browser go to: http://127.0.0.1:8080/
6. Test accounts are user with password user and admin with password admin

# **Keycloak setup**

Keycloak in Docker:

You can use the existing `docker-compose-keycloak-serv.yml` for creating keycloak server inside docker container.

Manual install:

This quick setup guide demonstrates installation for early test purposes running on localhost and default ports. Everything in Keycloak can be reconfigured to specific needs as well as Login screen template.
Keycloak is not needed to run test version of Taranis NG at the moment. You can use default _TestAuthenticator_ instead.
1. Requires JAVA 8 to run so download and install JDK from Oracle or OpenJDK e.g. `apt install openjdk-8-jdk`
2. Download keycloak from https://www.keycloak.org/downloads.html
3. In **keycloak-8.0.2/standalone/configuration/standalone.xml** change http listener port to 8081: `<socket-binding name="http" port="${jboss.http.port:8081}"/>`
4. Run keycloak in **keycloak-8.0.2/bin**: `sudo ./standalone.sh`
5. In browser go to http://127.0.0.1:8081/
6. Create first admin account and log in to Master Realm
7. Choose **ADD REALM** to create realm with the name **taranisng**
8. In taranis-ng realm choose **IMPORT** and import file _realm-export.json_ from **taranis-ng-core** root
9. In CLIENTS choose taranis-ng and regenerate secret in CREDENTIALS -> REGENERATE SECRET and put secret it _into client_secrets.json_ inside **taranis-ng-core** root (_NOTE: this will be properly configurable inside admin interface in the future_)
10. Create 2 users **user** and **admin** in USERS -> ADD USER. These are test users in Taranis NG at the moment.
11. In **taranis-ng-core** add environment variable TARANIS_NG_AUTHENTICATOR=openid (just for sign in) or TARANIS_NG_AUTHENTICATOR=keycloak (for identy management)
12. In **taranis-ng-core** add environment variable OPENID_LOGOUT_URL and set it according to your Keycloak installation
13. In **taranis-ng-gui** add these environment variables VUE_APP_TARANIS_NG_LOGIN_URL, VUE_APP_TARANIS_NG_LOGOUT_URL to activate external login:

## Keycloak client example of docker-compose.yml:

**taranis-ng-core** section:
```
TARANIS_NG_AUTHENTICATOR: "keycloak"
TARANIS_NG_KEYCLOAK_URL: "https://keycloak.example.com"
TARANIS_NG_KEYCLOAK_INTERNAL_URL: "https://keycloak.int.example.com"
TARANIS_NG_KEYCLOAK_CLIENT_ID: "taranis-ng"
OPENID_LOGOUT_URL: "${TARANIS_NG_KEYCLOAK_URL}/realms/taranis-ng/protocol/openid-connect/logout?redirect_uri=GOTO_URL"
KEYCLOAK_VERSION: "25.0.6"
KEYCLOAK_REALM_NAME: "taranis-ng"
KEYCLOAK_USER_MANAGEMENT: "false"
```

If you configure keycloak in client mode check this secret definition:
```
secrets:
    - keycloak_admin_password
```
and update key inside file:
```
./secrets/keycloak_client_secret_key.txt
```

If you configure keycloak also for administration check this secret definition:
```
secrets:
    - keycloak_admin_password
```
and update password inside file:
```
./secrets/keycloak_admin_password.txt
```


**taranis-ng-gui** section:
```
VUE_APP_TARANIS_NG_LOGIN_URL: "${TARANIS_NG_KEYCLOAK_URL}/realms/taranis-ng/protocol/openid-connect/auth?response_type=code&client_id=taranis-ng&redirect_uri=TARANIS_GUI_URI"
VUE_APP_TARANIS_NG_LOGOUT_URL: "${TARANIS_NG_KEYCLOAK_URL}/realms/taranis-ng/protocol/openid-connect/logout"
```

You can use and modify the existing `docker-compose-keycloak.yml` example in the repository and
run with ```docker-compose -f docker-compose.yml -f docker-compose-keycloak.yml```


# **LDAP setup**
If you prefer to authenticate users with LDAP, you need to set environment variables similarly to this:
```
TARANIS_NG_AUTHENTICATOR: "ldap"
LDAP_SERVER: "ldaps://ldap.example.com"
LDAP_BASE_DN: "ou=people,dc=example,dc=com"
LDAP_CA_CERT_PATH: "auth/ldap_ca.pem"
```
