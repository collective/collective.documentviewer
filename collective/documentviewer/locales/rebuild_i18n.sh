#!/bin/sh

DOMAIN="collective.documentviewer"
I18NDUDE=i18ndude
FINDPATH=..

# Synchronise the .pot with the templates.
${I18NDUDE} rebuild-pot \
          --pot ${FINDPATH}/locales/${DOMAIN}.pot \
          --merge ${FINDPATH}/locales/${DOMAIN}-manual.pot \
          --create ${DOMAIN} \
          ${FINDPATH}/
${I18NDUDE} rebuild-pot \
          --pot ${FINDPATH}/locales/plone.pot \
          --merge ${FINDPATH}/locales/plone-manual.pot \
          --exclude "../browser/templates/converting.pt" \
          --create plone \
          ${FINDPATH}/browser/templates/

# Synchronise the resulting .pot with the .po files
${I18NDUDE} sync \
          --pot ${FINDPATH}/locales/${DOMAIN}.pot \
          ${FINDPATH}/locales/*/LC_MESSAGES/${DOMAIN}.po
${I18NDUDE} sync \
          --pot ${FINDPATH}/locales/plone.pot \
          ${FINDPATH}/locales/*/LC_MESSAGES/plone.po

WARNINGS=`find \$FINDPATH/ -name '*pt' | xargs \${I18NDUDE} find-untranslated | grep -e '^-WARN' | wc -l`
ERRORS=`find \$FINDPATH/ -name '*pt' | xargs \${I18NDUDE} find-untranslated | grep -e '^-ERROR' | wc -l`
FATAL=`find \$FINDPATH/ -name '*pt' | xargs \${I18NDUDE} find-untranslated | grep -e '^-FATAL' | wc -l`

echo ""
echo "There are $WARNINGS warnings (possibly missing i18n markup)"
echo "There are $ERRORS errors (almost definitely missing i18n markup)"
echo "There are $FATAL fatal errors (template could not be parsed, eg. if it's not html)"

if [ -e $PWD/rebuild_i18n.log ]
then
    echo ""
    echo "Removing previous report for untranslated strings..."
    rm $PWD/rebuild_i18n.log
    echo "Adding a details report for untranslated strings..."
#    touch $PWD/rebuild_i18n.log
    find ${FINDPATH}/ -name '*pt' | xargs ${I18NDUDE} find-untranslated > $PWD/rebuild_i18n.log
else
    echo ""
    echo "Adding a details report for untranslated strings..."
#    touch $PWD/rebuild_i18n.log
    find ${FINDPATH}/ -name '*pt' | xargs ${I18NDUDE} find-untranslated > $PWD/rebuild_i18n.log
fi

echo ""
echo "For more details, run 'find $FINDPATH/ -name \"*pt\" | xargs $I18NDUDE find-untranslated' or"
echo "Look the rebuild i18n log generate for this script called 'rebuild_i18n.log' on locales dir"
# Ok, now your gettext files editor favorite is your friend!
