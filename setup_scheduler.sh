#!/bin/bash
#
# Setup Scheduler for Automatic Workflow Execution
# Configures cron job or systemd timer for nightly processing
#

set -e

echo "============================================================"
echo "🕐 SCHEDULER SETUP - Audio Processing Workflow"
echo "============================================================"

# Configuration
WORKFLOW_PATH="/home/sai/MCPClaude/audio_processing_workflow_v2.py"
PYTHON_PATH="/home/sai/whisper_env/bin/python3"
LOG_DIR="/home/sai/logs"
LOG_FILE="$LOG_DIR/workflow.log"

# Default schedule: 00:00 every day
DEFAULT_HOUR="0"
DEFAULT_MINUTE="0"

# Check if running as correct user
if [ "$USER" != "sai" ]; then
    echo "⚠️  This script should be run as user 'sai'"
    echo "Switch with: su - sai"
    exit 1
fi

echo ""
echo "📋 Configuration:"
echo "  Workflow: $WORKFLOW_PATH"
echo "  Python: $PYTHON_PATH"
echo "  Log: $LOG_FILE"
echo ""

# Ask for schedule time
read -p "Orario esecuzione (HH:MM, default 00:00): " input_time

if [ -z "$input_time" ]; then
    HOUR=$DEFAULT_HOUR
    MINUTE=$DEFAULT_MINUTE
else
    HOUR=$(echo $input_time | cut -d':' -f1)
    MINUTE=$(echo $input_time | cut -d':' -f2)
fi

echo ""
echo "⏰ Pianificato: Ogni giorno alle $HOUR:$MINUTE"
echo ""

# Choose method
echo "Scegli metodo di scheduling:"
echo "  1) Cron (semplice, standard)"
echo "  2) Systemd Timer (avanzato, più controllo)"
echo ""
read -p "Scelta (1 o 2): " method

# Create log directory
mkdir -p "$LOG_DIR"

case $method in
    1)
        echo ""
        echo "🔧 Configurazione Cron..."

        # Cron entry
        CRON_ENTRY="$MINUTE $HOUR * * * cd $(dirname $WORKFLOW_PATH) && $PYTHON_PATH $WORKFLOW_PATH >> $LOG_FILE 2>&1"

        # Check if already exists
        if crontab -l 2>/dev/null | grep -q "$WORKFLOW_PATH"; then
            echo "⚠️  Cron job già esistente!"
            read -p "Sostituire? (y/n): " replace

            if [ "$replace" = "y" ]; then
                # Remove old entry
                crontab -l | grep -v "$WORKFLOW_PATH" | crontab -

                # Add new entry
                (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

                echo "✅ Cron job aggiornato!"
            else
                echo "⏭️  Mantenuto cron job esistente"
            fi
        else
            # Add new entry
            (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

            echo "✅ Cron job creato!"
        fi

        echo ""
        echo "📋 Cron job installato:"
        echo "  $CRON_ENTRY"
        echo ""
        echo "Per verificare: crontab -l"
        echo "Per editare: crontab -e"
        echo "Per rimuovere: crontab -e (cancella la riga)"
        ;;

    2)
        echo ""
        echo "🔧 Configurazione Systemd Timer..."

        # Create systemd service
        SERVICE_FILE="/tmp/audio-workflow.service"
        TIMER_FILE="/tmp/audio-workflow.timer"

        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Audio Processing Workflow
After=network.target

[Service]
Type=oneshot
User=sai
WorkingDirectory=$(dirname $WORKFLOW_PATH)
Environment="PATH=/home/sai/whisper_env/bin:/usr/bin:/bin"
ExecStart=$PYTHON_PATH $WORKFLOW_PATH
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

[Install]
WantedBy=multi-user.target
EOF

        cat > "$TIMER_FILE" << EOF
[Unit]
Description=Audio Processing Workflow Timer
Requires=audio-workflow.service

[Timer]
OnCalendar=*-*-* $HOUR:$MINUTE:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

        echo "✅ File generati:"
        echo "  Service: $SERVICE_FILE"
        echo "  Timer: $TIMER_FILE"
        echo ""
        echo "Per installare, esegui come root:"
        echo ""
        echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
        echo "  sudo cp $TIMER_FILE /etc/systemd/system/"
        echo "  sudo systemctl daemon-reload"
        echo "  sudo systemctl enable audio-workflow.timer"
        echo "  sudo systemctl start audio-workflow.timer"
        echo ""
        echo "Per verificare:"
        echo "  sudo systemctl status audio-workflow.timer"
        echo "  sudo systemctl list-timers"
        echo ""
        echo "Per test manuale:"
        echo "  sudo systemctl start audio-workflow.service"
        ;;

    *)
        echo "❌ Scelta non valida"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "✅ SCHEDULER CONFIGURATO!"
echo "============================================================"
echo ""
echo "🎯 Prossima esecuzione: Ogni giorno alle $HOUR:$MINUTE"
echo "📄 Logs salvati in: $LOG_FILE"
echo ""
echo "📋 Comandi utili:"
echo "  • View logs: tail -f $LOG_FILE"
echo "  • Test manuale: $PYTHON_PATH $WORKFLOW_PATH"

case $method in
    1)
        echo "  • List cron: crontab -l"
        echo "  • Edit cron: crontab -e"
        ;;
    2)
        echo "  • Status: sudo systemctl status audio-workflow.timer"
        echo "  • Start now: sudo systemctl start audio-workflow.service"
        echo "  • Stop: sudo systemctl stop audio-workflow.timer"
        ;;
esac

echo ""
echo "🚀 Sistema pronto per esecuzione automatica!"
