"""
Quick script to test Railway Postgres connectivity.
Run: python test_railway_db.py

You'll be prompted for the connection details from your Railway dashboard.
Go to: Railway project → Postgres service → "Data" or "Connect" tab → copy the values.
"""
import getpass
import sys

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

print("=" * 60)
print("  Railway Postgres Connection Tester")
print("=" * 60)
print()
print("Go to your Railway dashboard:")
print("  Project → Click on the Postgres service → 'Data' tab or 'Variables' tab")
print("  Copy the values below exactly as shown.")
print()

host = input("PGHOST (e.g. postgres-isnm.railway.internal or the public host): ").strip()
port = input("PGPORT [5432]: ").strip() or "5432"
database = input("PGDATABASE [railway]: ").strip() or "railway"
user = input("PGUSER [postgres]: ").strip() or "postgres"
password = getpass.getpass("PGPASSWORD (paste it, it will be hidden): ").strip()

print()
print(f"  Host     : {host}")
print(f"  Port     : {port}")
print(f"  Database : {database}")
print(f"  User     : {user}")
print(f"  Password : {'*' * len(password)} ({len(password)} chars)")
print()

# Railway internal hosts won't be reachable from your local machine.
# If they gave the internal host, tell them to use the public one.
if ".railway.internal" in host:
    print("⚠  You entered the INTERNAL host which is only reachable from inside Railway.")
    print("   For local testing, use the PUBLIC host instead.")
    print("   Go to Railway → Postgres service → 'Connect' tab → look for the public host.")
    print("   It usually looks like: xxx.railway.app or roundhouse.proxy.rlwy.net")
    print()
    host = input("Enter the PUBLIC host: ").strip()
    port = input(f"Enter the PUBLIC port [{port}]: ").strip() or port
    print()

print("Attempting connection...")
try:
    conn = psycopg2.connect(
        host=host,
        port=int(port),
        dbname=database,
        user=user,
        password=password,
        connect_timeout=10,
        sslmode="require",
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    cur.close()
    conn.close()
    print()
    print("✅ CONNECTION SUCCESSFUL!")
    print(f"   {version}")
    print()
    print("The credentials work. Make sure these EXACT values are set as")
    print("variable references on your Railway BACKEND service.")
except Exception as e:
    print()
    print(f"❌ CONNECTION FAILED: {e}")
    print()
    print("If 'password authentication failed':")
    print("  1. Go to Railway → Postgres service → 'Variables' tab")
    print("  2. Find PGPASSWORD — copy it exactly")
    print("  3. On the BACKEND service → Variables, make sure PGPASSWORD")
    print("     is a ${{Postgres.PGPASSWORD}} reference, NOT a manual string.")
    print()
    print("If still failing, RESET the password:")
    print("  Railway → Postgres service → Settings → scroll to 'Reset Credentials'")
