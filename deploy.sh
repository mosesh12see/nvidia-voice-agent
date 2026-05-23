#!/bin/bash
# Deploy nvidia-voice-agent to 157.230.13.249
# Run from your Mac: bash deploy.sh

set -e
SERVER=157.230.13.249
DEST=/opt/nvidia-voice-agent

echo "Deploying to $SERVER..."

# Copy project files
ssh root@$SERVER "mkdir -p $DEST/agi $DEST/agent $DEST/campaigns $DEST/dialplan"
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  ./ root@$SERVER:$DEST/

# Install dependencies
ssh root@$SERVER "cd $DEST && pip3 install -r requirements.txt"

# Set up .env if it doesn't exist
ssh root@$SERVER "[ -f $DEST/.env ] || cp $DEST/env.example $DEST/.env && echo 'Created .env from env.example — fill in your keys'"

# Make AGI script executable
ssh root@$SERVER "chmod +x $DEST/agi/nvidia_agent.agi"

# Install systemd service
ssh root@$SERVER "cp $DEST/systemd/nvidia-agent.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable nvidia-agent"

# Copy dialplan snippet
ssh root@$SERVER "mkdir -p /etc/asterisk/includes && cp $DEST/dialplan/nvidia-agent.conf /etc/asterisk/includes/"

echo ""
echo "Done. Next steps on the server:"
echo "  1. Edit $DEST/.env and add your API keys"
echo "  2. Add to /etc/asterisk/extensions.conf:"
echo "       #include \"includes/nvidia-agent.conf\""
echo "  3. systemctl start nvidia-agent"
echo "  4. asterisk -rx 'dialplan reload'"
echo "  5. Test by calling extension 8400"
