#!/usr/bin/env sh
set -euxo pipefail

/usr/local/bin/platypus --droppable --app-icon '/private/var/folders/p_/99ybd0g95x7_69wgnqnkv8p40000gn/T/AppTranslocation/72D75CBD-C50E-4A12-B450-360A290D68AA/d/Platypus.app/Contents/Resources/PlatypusDefault.icns'  --name 'automarimo'  --interface-type 'None'  --interpreter '/usr/bin/python3'  --author 'csp256'   --bundle-identifier org.csp256.automarimo --uniform-type-identifiers 'public.item|public.folder|public.python-script|dyn.ah62d4rv4ge80w6d3r3va'  './automarimo.py'