#!/bin/bash
set -e

cat << 'EOF' 

 .----------------.  .----------------.  .----------------.  .----------------.
| .--------------. || .--------------. || .--------------. || .--------------. |
| |  ____  ____  | || |     ____     | || |  _________   | || |      __      | |
| | |_   ||   _| | || |   .'    `.   | || | |  _   _  |  | || |     /  \     | |
| |   | |\/| |   | || |  /  .--.  \  | || | |_/ | | \_|  | || |    / /\ \    | |
| |   | |  | |   | || |  | |    | |  | || |     | |      | || |   / ____ \   | |
| |  _| |_ | |_  | || |  \  `--'  /  | || |    _| |_     | || | _/ /    \ \_ | |
| | |____||____| | || |   `.____.'   | || |   |_____|    | || ||____|  |____|| |
| |              | || |              | || |              | || |              | |
| '--------------' || '--------------' || '--------------' || '--------------' |
 '----------------'  '----------------'  '----------------'  '----------------'

EOF

echo "📡 Starting container..."

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "🛠️ Running migrations..."
  python manage.py migrate --noinput

  echo "📦 Collecting static files..."
  python manage.py collectstatic --noinput --clear

  echo "🌍 Compiling translation messages (en, fr, de, es)..."
  python manage.py compilemessages
else
  echo "⏭️ Skipping migrations/static tasks for this container"
fi

echo "🚀 Starting: $@"
exec "$@" 