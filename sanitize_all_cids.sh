#!/bin/bash

# Script de nettoyage COMPLET de tous les CIDs et identifiants sensibles
# Remplace TOUS les CIDs réels par des valeurs fictives

echo "🧹 Nettoyage complet des CIDs et identifiants sensibles..."

# Fonction pour remplacer dans tous les fichiers .md
sanitize_file() {
    local file="$1"
    if [ -f "$file" ]; then
        echo "  📄 Nettoyage: $file"

        # CID Names
        sed -i 's/SE FR FCTL - Servers/Production Servers/g' "$file"
        sed -i 's/SE FR FCTL - Workstations A/Development Workstations A/g' "$file"
        sed -i 's/SE FR FCTL - Workstations B/Development Workstations B/g' "$file"
        sed -i 's/SE FR FCTL - Workstations Global/Enterprise Workstations/g' "$file"

        # CID IDs (32-char hex) - Réels
        sed -i 's/6946f672680e49448ef343eddf5dd9d7/a1b2c3d4e5f6789012345678901234ab/g' "$file"
        sed -i 's/8cda703d324344b69b3ee4513b1940e4/b2c3d4e5f678901234567890123456bc/g' "$file"
        sed -i 's/66aa77b2550341a8978769265e616af4/c3d4e5f67890123456789012345678cd/g' "$file"
        sed -i 's/6638b9148787417d9664fc99107dc31f/d4e5f678901234567890123456789def/g' "$file"

        # Parent CID qui était dans manual_replication_guide
        sed -i 's/ac4a7606096941a4b63d8a9b226f49b2/a1b2c3d4e5f6789012345678901234ab/g' "$file"

        # Role IDs (remplacer par des UUIDs fictifs génériques)
        sed -i 's/71078f5c73a44ae09be31c9116c81c20/11111111111111111111111111111111/g' "$file"
        sed -i 's/89cf004ef6f64a29956c0e64b11a1972/22222222222222222222222222222222/g' "$file"
        sed -i 's/aa2452cef20f4c39a6cc78f492485848/33333333333333333333333333333333/g' "$file"
        sed -i 's/03455110e32b49caa701c3e4571519dd/44444444444444444444444444444444/g' "$file"
        sed -i 's/346cbb107a2d4833b22a5f69e1f14b4c/55555555555555555555555555555555/g' "$file"
        sed -i 's/4ebf377b2bd9434b8c236a671e46b417/66666666666666666666666666666666/g' "$file"
        sed -i 's/6ef2c3e007894bf08ed4d68d937fd5de/77777777777777777777777777777777/g' "$file"

        # Device IDs
        sed -i 's/93cf90e6c30545ffbe3ebce3a7548e71/f9e8d7c6b5a4321098765432109876cd/g' "$file"

        # Hostnames
        sed -i 's/SE-VMA-W2019-DT/PROD-WEB-01/g' "$file"

        # AWS Account IDs
        sed -i 's/517716713836/123456789012/g' "$file"
    fi
}

# Nettoyer tous les fichiers .md récursivement
find . -name "*.md" -type f | while read file; do
    sanitize_file "$file"
done

echo ""
echo "✅ Nettoyage terminé!"
echo ""
echo "🔍 Vérification des CIDs restants..."

# Vérifier s'il reste des CIDs réels
REMAINING=$(grep -r "6946f672680e\|8cda703d3243\|66aa77b25503\|6638b9148787\|ac4a7606096941a4b63d8a9b226f49b2\|93cf90e6c305\|517716713836" . --include="*.md" --include="*.py" 2>/dev/null | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Aucun CID réel détecté!"
else
    echo "⚠️  $REMAINING occurrence(s) trouvée(s):"
    grep -rn "6946f672680e\|8cda703d3243\|66aa77b25503\|6638b9148787\|ac4a7606096941a4b63d8a9b226f49b2\|93cf90e6c305\|517716713836" . --include="*.md" --include="*.py" 2>/dev/null
fi

echo ""
echo "📊 Résumé des fichiers nettoyés:"
find . -name "*.md" -type f | wc -l
echo " fichiers .md traités"
