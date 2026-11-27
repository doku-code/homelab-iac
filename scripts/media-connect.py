#!/usr/bin/env python3
"""Connects the applications of the media stack to each other through their own APIs (TASK-036).

Run from the workstation by `make media-connect`, with the credentials in the environment and the containers'
addresses in MEDIA_ADDRESSES. Every step looks first and writes only what is missing, so a second run changes
nothing ("changed: " lines say what was written). No credential is ever printed.

  Jellyfin   first administrator (the setup wizard's own endpoints), the libraries of the test area and of
             the NAS share, hardware transcoding when the container has the graphics device
  Radarr     its administrator, the test root folder, the NAS's qBittorrent as download client
  Sonarr     the same
  Prowlarr   its administrator, Radarr and Sonarr as applications (indexers are then pushed to both)
  Seerr      first administrator (the Jellyfin one), Jellyfin's libraries, Radarr and Sonarr with the test folders
"""
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ADMIN = os.environ["MEDIA_ADMIN_USER"]
PASSWORD = os.environ["MEDIA_ADMIN_PASSWORD"]
KEYS = {name: os.environ[f"{name.upper()}_API_KEY"] for name in ("radarr", "sonarr", "prowlarr", "seerr")}
TEST_MOVIES = os.environ["MEDIA_TEST_MOVIES"]
TEST_SERIES = os.environ["MEDIA_TEST_SERIES"]
NAS_LIBRARIES = json.loads(os.environ.get("MEDIA_NAS_LIBRARIES") or "[]")
GPU = os.environ.get("MEDIA_GPU") == "yes"
GPU_DEVICE = os.environ.get("MEDIA_GPU_DEVICE", "/dev/dri/renderD128")
NAS_LIBRARY = os.environ.get("MEDIA_NAS_LIBRARY", "/media/plex")
ADDRESSES = json.loads(os.environ["MEDIA_ADDRESSES"])
QBITTORRENT = urllib.parse.urlsplit(os.environ["MEDIA_QBIT_URL"])
QBIT_USER, QBIT_PASSWORD = os.environ["MEDIA_QBIT_USERNAME"], os.environ["MEDIA_QBIT_PASSWORD"]
MEDIA_URL = os.environ.get("MEDIA_URL", "")
JELLYFIN_URL = os.environ.get("MEDIA_JELLYFIN_URL", "")
SECRETS = [PASSWORD, QBIT_PASSWORD, *KEYS.values()]
# "local" is how this script reaches an application; "inside" is how the applications reach each other: by the
# container's name, which every container has in its /etc/hosts (role media_service).
ARR = {
    "radarr": {"local": f"http://{ADDRESSES['radarr']}:7878/radarr", "inside": "http://radarr:7878/radarr", "api": "api/v3", "port": 7878,
               "root": TEST_MOVIES, "category_field": "movieCategory"},
    "sonarr": {"local": f"http://{ADDRESSES['sonarr']}:8989/sonarr", "inside": "http://sonarr:8989/sonarr", "api": "api/v3", "port": 8989,
               "root": TEST_SERIES, "category_field": "tvCategory"},
    "prowlarr": {"local": f"http://{ADDRESSES['prowlarr']}:9696/prowlarr", "inside": "http://prowlarr:9696/prowlarr", "api": "api/v1", "port": 9696},
}
JELLYFIN = f"http://{ADDRESSES['jellyfin']}:8096"
SEERR = f"http://{ADDRESSES['seerr']}:5055/api/v1"
CLIENT = 'MediaBrowser Client="homelab-iac", Device="workstation", DeviceId="homelab-iac-media-connect", Version="1"'


class Failed(Exception):
    pass


def redact(text):
    for secret in SECRETS:
        text = text.replace(secret, "***")
    return text


def changed(message):
    print(f"changed: {message}")


def call(method, url, body=None, headers=None, opener=None, expect=(200, 201, 202, 204), form=False):
    data = None
    headers = dict(headers or {})
    if body is not None:
        data = urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded" if form else "application/json")
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with (opener.open(request, timeout=60) if opener else urllib.request.urlopen(request, timeout=60)) as response:
            status, text = response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        status, text = error.code, error.read().decode("utf-8", "replace")
    if status not in expect:
        raise Failed(f"{method} {url.split('?')[0]}: HTTP {status}: {redact(text)[:300]}")
    try:
        return json.loads(text) if text.strip() else None
    except ValueError:
        return text


# ── Servarr tools ─────────────────────────────────────────────────────────────────────────────────────────

def arr(name, method, path, body=None):
    app = ARR[name]
    return call(method, f"{app['local']}/{app['api']}/{path}", body, {"X-Api-Key": KEYS[name]})


def arr_administrator(name):
    """The application's own sign-in (Forms). The method and when it is asked come from the environment."""
    host = arr(name, "GET", "config/host")
    if host.get("username") == ADMIN:
        return
    host.update({"username": ADMIN, "password": PASSWORD, "passwordConfirmation": PASSWORD})
    if "allowedHosts" in host:
        # Newer releases want the names the application is called by when its sign-in is not asked everywhere:
        # the published name (Traefik), the container's name (the other containers) and its address.
        published = urllib.parse.urlsplit(MEDIA_URL).hostname
        host["allowedHosts"] = ",".join(filter(None, [published, name, ADDRESSES[name], "localhost", "127.0.0.1"]))
    arr(name, "PUT", f"config/host/{host['id']}", host)
    changed(f"{name}: administrator {ADMIN} created (password: store path /media)")


def arr_root_folder(name):
    wanted = ARR[name]["root"]
    folders = [folder["path"].rstrip("/") for folder in arr(name, "GET", "rootfolder")]
    if wanted in folders:
        return
    arr(name, "POST", "rootfolder", {"path": wanted})
    changed(f"{name}: root folder {wanted} (the test area)")


def arr_download_client(name):
    if any(client["implementation"] == "QBittorrent" for client in arr(name, "GET", "downloadclient")):
        return
    (schema,) = [s for s in arr(name, "GET", "downloadclient/schema") if s["implementation"] == "QBittorrent"]
    values = {"host": QBITTORRENT.hostname, "port": QBITTORRENT.port, "useSsl": QBITTORRENT.scheme == "https",
              "username": QBIT_USER, "password": QBIT_PASSWORD, ARR[name]["category_field"]: name}
    for field in schema["fields"]:
        if field["name"] in values:
            field["value"] = values[field["name"]]
    # The client is the operator's own, with their torrents: nothing is ever removed from it.
    schema.update({"name": "qBittorrent (NAS)", "enable": True, "priority": 1,
                   "removeCompletedDownloads": False, "removeFailedDownloads": False})
    # The application tests the connection before it saves: a wrong password or an absent client fails here.
    arr(name, "POST", "downloadclient", schema)
    changed(f"{name}: download client qBittorrent on the NAS, category {name}")


def prowlarr_application(name):
    if any(application["implementation"].lower() == name for application in arr("prowlarr", "GET", "applications")):
        return
    (schema,) = [s for s in arr("prowlarr", "GET", "applications/schema") if s["implementation"].lower() == name]
    values = {"prowlarrUrl": ARR["prowlarr"]["inside"], "baseUrl": ARR[name]["inside"], "apiKey": KEYS[name]}
    for field in schema["fields"]:
        if field["name"] in values:
            field["value"] = values[field["name"]]
    schema.update({"name": name.capitalize(), "syncLevel": "fullSync"})
    arr("prowlarr", "POST", "applications", schema)
    changed(f"prowlarr: application {name.capitalize()} (indexers are pushed to it)")


# ── Jellyfin ──────────────────────────────────────────────────────────────────────────────────────────────

def jellyfin(method, path, body=None, token=None, expect=(200, 204)):
    authorization = CLIENT + (f', Token="{token}"' if token else "")
    return call(method, f"{JELLYFIN}{path}", body, {"Authorization": authorization}, expect=expect)


def jellyfin_administrator():
    """The setup wizard, through the endpoints the wizard itself calls; only while it has never been completed."""
    if jellyfin("GET", "/System/Info/Public")["StartupWizardCompleted"]:
        return
    jellyfin("POST", "/Startup/Configuration", {"UICulture": "en-US", "MetadataCountryCode": "CA", "PreferredMetadataLanguage": "en"})
    jellyfin("GET", "/Startup/User")  # creates the first user, which the next call names
    jellyfin("POST", "/Startup/User", {"Name": ADMIN, "Password": PASSWORD})
    jellyfin("POST", "/Startup/RemoteAccess", {"EnableRemoteAccess": True, "EnableAutomaticPortMapping": False})
    jellyfin("POST", "/Startup/Complete")
    changed(f"jellyfin: setup completed, administrator {ADMIN} created (password: store path /media)")


def jellyfin_libraries(token):
    wanted = [("Test movies", "movies", TEST_MOVIES), ("Test series", "tvshows", TEST_SERIES)]
    wanted += [(library["name"], library["type"], NAS_LIBRARY + "/" + library["path"].strip("/")) for library in NAS_LIBRARIES]
    existing = {folder["Name"]: folder.get("Locations", []) for folder in jellyfin("GET", "/Library/VirtualFolders", token=token)}
    for name, kind, path in wanted:
        if name in existing:
            if path not in existing[name]:
                print(f"review: jellyfin library {name} exists with {existing[name]}, not {path}; left as it is")
            continue
        query = urllib.parse.urlencode({"name": name, "collectionType": kind, "refreshLibrary": "true"})
        # Real-time monitoring works on the node's own disk; a network share is found by the scheduled scan.
        options = {"PathInfos": [{"Path": path}], "EnableRealtimeMonitor": not path.startswith(NAS_LIBRARY + "/")}
        jellyfin("POST", f"/Library/VirtualFolders?{query}", {"LibraryOptions": options}, token=token)
        changed(f"jellyfin: library {name} ({kind}) on {path}")


def jellyfin_transcoding(token):
    """VA-API on the node's graphics device. Jasper Lake encodes in low-power mode only; no AV1 on this chip."""
    if not GPU:
        return
    encoding = jellyfin("GET", "/System/Configuration/encoding", token=token)
    wanted = {
        "HardwareAccelerationType": "vaapi", "VaapiDevice": GPU_DEVICE, "EnableHardwareEncoding": True,
        "EnableIntelLowPowerH264HwEncoder": True, "EnableIntelLowPowerHevcHwEncoder": True,
        "HardwareDecodingCodecs": ["h264", "hevc", "mpeg2video", "vc1", "vp8", "vp9"],
        "EnableDecodingColorDepth10Hevc": True, "EnableDecodingColorDepth10Vp9": True,
        "AllowHevcEncoding": False, "AllowAv1Encoding": False,
    }
    if all(encoding.get(key) == value for key, value in wanted.items()):
        return
    encoding.update(wanted)
    jellyfin("POST", "/System/Configuration/encoding", encoding, token=token)
    changed(f"jellyfin: hardware transcoding through VA-API on {GPU_DEVICE}, low-power encoders")


# ── Seerr ─────────────────────────────────────────────────────────────────────────────────────────────────

def seerr(method, path, body=None, opener=None):
    headers = {} if opener else {"X-Api-Key": KEYS["seerr"]}
    return call(method, f"{SEERR}/{path}", body, headers, opener=opener)


def seerr_setup():
    """First sign-in with Jellyfin's administrator: Seerr then knows Jellyfin and has its own administrator."""
    if seerr("GET", "settings/public")["initialized"]:
        return
    session = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    first = {"username": ADMIN, "password": PASSWORD, "hostname": "jellyfin", "port": 8096, "useSsl": False, "urlBase": "",
             "email": f"{ADMIN}@doku-lab.net", "serverType": 2}
    try:
        # Nobody exists yet, so nothing but this sign-in is allowed (the API key belongs to the first user).
        seerr("POST", "auth/jellyfin", first, opener=session)
        changed("seerr: connected to Jellyfin, its administrator is Jellyfin's")
    except Failed:
        # A run that stopped between the sign-in and the end of the setup: Jellyfin is already known.
        seerr("POST", "auth/jellyfin", {"username": ADMIN, "password": PASSWORD}, opener=session)
    seerr("POST", "settings/initialize", opener=session)
    changed("seerr: setup completed")


def seerr_libraries():
    """Seerr reads Jellyfin's libraries again (new ones appear, enabled ones stay so) and every one is enabled."""
    libraries = seerr("POST", "settings/jellyfin/library/sync")
    for library in libraries:
        if not library["enabled"]:
            seerr("PUT", f"settings/jellyfin/library/{library['id']}", {"enabled": True})
            changed(f"seerr: Jellyfin library {library['name']} enabled")


def seerr_external_address():
    settings = seerr("GET", "settings/jellyfin")
    if not JELLYFIN_URL or settings.get("externalHostname") == JELLYFIN_URL:
        return
    writable = ("ip", "port", "useSsl", "urlBase", "jellyfinForgotPasswordUrl", "apiKey")
    seerr("POST", "settings/jellyfin", {**{key: settings[key] for key in writable if key in settings}, "externalHostname": JELLYFIN_URL})
    changed(f"seerr: links to Jellyfin lead to {JELLYFIN_URL}")


def seerr_arr(name):
    """Requests go to the test folder, with the application's standard 1080p profile."""
    if seerr("GET", f"settings/{name}"):
        return
    profiles = arr(name, "GET", "qualityprofile")
    profile = next((p for p in profiles if p["name"] == "HD-1080p"), profiles[0])
    server = {"name": name.capitalize(), "hostname": name, "port": ARR[name]["port"], "apiKey": KEYS[name], "useSsl": False,
              "baseUrl": f"/{name}", "activeProfileId": profile["id"], "activeProfileName": profile["name"],
              "activeDirectory": ARR[name]["root"], "is4k": False, "isDefault": True, "syncEnabled": True,
              "preventSearch": False, "externalUrl": f"{MEDIA_URL}/{name}" if MEDIA_URL else ""}
    if name == "radarr":
        server["minimumAvailability"] = "released"
    else:
        server.update({"seriesType": "standard", "animeSeriesType": "anime", "enableSeasonFolders": True})
    seerr("POST", f"settings/{name}", server)
    changed(f"seerr: {name.capitalize()} with {ARR[name]['root']} and profile {profile['name']}")


def qbittorrent_sign_in():
    """Only checks that the NAS's qBittorrent accepts the sign-in of the store; nothing is changed in it."""
    base = QBITTORRENT.geturl().rstrip("/")
    try:
        # 204 since qBittorrent 5.2, "Ok." with 200 before; a wrong password answers 401 (or "Fails." with 200).
        answer = call("POST", f"{base}/api/v2/auth/login", {"username": QBIT_USER, "password": QBIT_PASSWORD}, form=True,
                      headers={"Referer": base}, expect=(200, 204))
    except Failed:
        answer = "Fails."
    if isinstance(answer, str) and not answer.startswith("Ok"):
        raise Failed("qbittorrent: the NAS's qBittorrent refuses the sign-in of the store (path /homepage)")


def main():
    qbittorrent_sign_in()
    for name in ("radarr", "sonarr", "prowlarr"):
        arr_administrator(name)
    for name in ("radarr", "sonarr"):
        arr_root_folder(name)
        arr_download_client(name)
        prowlarr_application(name)
    jellyfin_administrator()
    token = jellyfin("POST", "/Users/AuthenticateByName", {"Username": ADMIN, "Pw": PASSWORD})["AccessToken"]
    try:
        jellyfin_libraries(token)
        jellyfin_transcoding(token)
    finally:
        jellyfin("POST", "/Sessions/Logout", token=token)
    seerr_setup()
    seerr_libraries()
    seerr_external_address()
    for name in ("radarr", "sonarr"):
        seerr_arr(name)
    print("connected: qBittorrent (NAS) <- Radarr, Sonarr <- Prowlarr; Jellyfin <- Seerr -> Radarr, Sonarr")


if __name__ == "__main__":
    try:
        main()
    except Failed as failure:
        print(f"media-connect: {failure}", file=sys.stderr)
        sys.exit(1)
