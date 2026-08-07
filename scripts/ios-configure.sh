#!/usr/bin/env bash
# Configure le projet iOS généré par Capacitor (exécuté sur le Mac cloud, après `cap sync ios`).
# - Injecte les textes d'autorisation (Info.plist) + drapeau chiffrement export.
# - Ajoute le Privacy Manifest (PrivacyInfo.xcprivacy) aux ressources du target.
# - Active la capability Push Notifications.
# Idempotent : peut tourner à chaque build.
set -euo pipefail

APP_DIR="ios/App"
PLIST="$APP_DIR/App/Info.plist"
PB=/usr/libexec/PlistBuddy

echo "==> Injection des clés Info.plist"
set_str() { $PB -c "Delete :$1" "$PLIST" 2>/dev/null || true; $PB -c "Add :$1 string $2" "$PLIST"; }
set_bool() { $PB -c "Delete :$1" "$PLIST" 2>/dev/null || true; $PB -c "Add :$1 bool $2" "$PLIST"; }

set_str NSCameraUsageDescription "DIVARC utilise l'appareil photo pour tes publications et ton profil."
set_str NSPhotoLibraryUsageDescription "DIVARC accède à tes photos pour illustrer tes publications et ton profil."
set_str NSPhotoLibraryAddUsageDescription "DIVARC enregistre des images dans ta photothèque à ta demande."
set_str NSFaceIDUsageDescription "DIVARC utilise Face ID pour protéger l'accès à ton compte."
set_str NSLocationWhenInUseUsageDescription "DIVARC utilise ta position approximative (jamais exacte) pour les rencontres et contenus proches."
set_str NSMicrophoneUsageDescription "DIVARC utilise le micro pour les appels audio et vidéo."
set_bool ITSAppUsesNonExemptEncryption false

echo "==> Copie du Privacy Manifest"
cp -f ios-config/PrivacyInfo.xcprivacy "$APP_DIR/App/PrivacyInfo.xcprivacy"

echo "==> Ajout du manifest aux ressources + capability Push (via xcodeproj)"
gem list xcodeproj -i >/dev/null 2>&1 || gem install xcodeproj --no-document
ruby - "$APP_DIR/App.xcodeproj" <<'RUBY'
require 'xcodeproj'
proj_path = ARGV[0]
proj = Xcodeproj::Project.open(proj_path)
target = proj.targets.find { |t| t.name == 'App' } || proj.targets.first
group = proj.main_group.find_subpath('App', true)

# 1) Ajoute PrivacyInfo.xcprivacy aux ressources si absent
unless proj.files.any? { |f| f.path && f.path.end_with?('PrivacyInfo.xcprivacy') }
  ref = group.new_reference('PrivacyInfo.xcprivacy')
  target.add_resources([ref])
  puts 'PrivacyInfo.xcprivacy ajouté aux ressources'
end

# 2) Active Push Notifications (aps-environment via entitlements)
ent_path = 'App/App.entitlements'
full_ent = File.join(File.dirname(proj_path), ent_path)
unless File.exist?(full_ent)
  File.write(full_ent, {'aps-environment' => 'production'}.to_plist)
  ref = group.new_reference('App.entitlements')
  puts 'App.entitlements créé'
end
target.build_configurations.each do |c|
  c.build_settings['CODE_SIGN_ENTITLEMENTS'] = 'App/App.entitlements'
end

proj.save
RUBY
echo "==> iOS configuré."
