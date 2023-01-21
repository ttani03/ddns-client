import ipaddress
import os
import sys

import click
import dns.query
import dns.tsigkeyring
import dns.update
import dns.zone


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = {}

    key_name = os.environ.get("DDNS_KEY_NAME")
    key_secret = os.environ.get("DDNS_KEY_SECRET")
    if key_name is None or key_secret is None:
        click.echo("DDNS_KEY_NAME or DDNS_KEY_SECRET is not defined.")
        sys.exit(1)
    ctx.obj["keyring"] = dns.tsigkeyring.from_text({key_name: key_secret})

    domain = os.environ.get("DDNS_DOMAIN")
    ddns_server = os.environ.get("DDNS_SERVER")
    if domain is None or ddns_server is None:
        click.echo("DDNS_DOMAIN or DDNS_SERVER is not defined.", err=True)
        sys.exit(1)
    ctx.obj["domain"] = domain
    ctx.obj["ddns_server"] = ddns_server


@cli.command()
@click.pass_obj
@click.option("-n", "--host", required=True, type=str, help="Specify a hostname")
@click.option(
    "-t", "--ttl", required=False, type=int, default=3600, help="TTL (default: 3600)"
)
@click.option("-i", "--ipaddr", type=str, required=True, help="IP address")
def add(obj, host: str, ttl: int, ipaddr: str):
    try:
        ipaddress.ip_address(ipaddr)
    except ValueError:
        click.echo("Invalid IP address.", err=True)
        sys.exit(1)

    update = dns.update.UpdateMessage(obj["domain"], keyring=obj["keyring"])
    update.replace(host, ttl, "A", ipaddr)
    dns.query.tcp(update, obj["ddns_server"], timeout=10)


@cli.command()
@click.pass_obj
@click.option("-n", "--host", required=True, type=str, help="Specify a hostname")
def delete(obj, host: str):
    update = dns.update.UpdateMessage(obj["domain"], keyring=obj["keyring"])
    update.delete(host)
    dns.query.tcp(update, obj["ddns_server"], timeout=10)


@cli.command()
@click.pass_obj
def get(obj):
    zone = dns.zone.from_xfr(
        dns.query.xfr(
            where=obj["ddns_server"], zone=obj["domain"], keyring=obj["keyring"]
        )
    )
    for n in zone.nodes.keys():
        r = zone[n].to_text(n).split(" ")
        if r[3] == "A":
            print("{0:<10} | {1:<15}".format(r[0], r[4]))


def main():
    cli()
    sys.exit(0)


if __name__ == "__main__":
    main()
