#!/usr/bin/env python3
#
# Wireshark - Network traffic analyzer
# By Gerald Combs <gerald@wireshark.org>
# Copyright 1998 Gerald Combs
#
# SPDX-License-Identifier: GPL-2.0-or-later
'''Update the "manuf" file.

Make-manuf creates a file containing ethernet OUIs and their company
IDs. It merges the databases at IEEE with entries in our template file.
Our file in turn contains entries from
http://www.cavebear.com/archive/cavebear/Ethernet/Ethernet.txt along
with our own.

The script reads the comments at the top of "manuf.tmpl" and writes them
to "manuf".  It then joins the manufacturer listing in "manuf.tmpl" with
the listing in "oui.txt", "iab.txt", etc, with the entries in
"manuf.tmpl" taking precedence.
'''

import csv
import html
import io
import os
import re
import sys
import urllib.request, urllib.error, urllib.parse

max_o = 0
max_a = 0
def updatemaxo(l):
    global max_o
    if l > max_o:
        max_o = l

def updatemaxa(l):
    global max_a
    if l > max_a:
        max_a = l

def exit_msg(msg=None, status=1):
    if msg is not None:
        sys.stderr.write(msg + '\n\n')
    sys.stderr.write(__doc__ + '\n')
    sys.exit(status)

def open_url(path):
    '''Open a URL.
    Returns a tuple containing the body and response dict. The body is a
    str in Python 3 and bytes in Python 2 in order to be compatibile with
    csv.reader.
    '''
    req_headers = { 'User-Agent': 'Wireshark make-manuf' }
    url = "http://standards-oui.ieee.org" + path
    # url = "http://127.0.0.1:8080/cache/standards-oui.ieee.org" + path
    try:
        req = urllib.request.Request(url, headers=req_headers)
        response = urllib.request.urlopen(req)
        body = response.read().decode('UTF-8', 'replace')
    except Exception:
        exit_msg('Error opening ' + url)

    return (body, dict(response.info()))

# These are applied after punctuation has been removed.
# More examples at https://en.wikipedia.org/wiki/Incorporation_(business)
general_terms = '|'.join([
    'a +s', # A/S and A.S. but not "As" as in "Connect As".
    'ab', # Also follows "Oy", which is covered below.
    'ag',
    'b ?v',
    'closed joint stock company',
    'co',
    'company',
    'corp',
    'corporation',
    'de c ?v', # Follows "S.A.", which is covered separately below.
    'gmbh',
    'holding',
    'inc',
    'incorporated',
    'jsc',
    'kg',
    'k k', # "K.K." as in "kabushiki kaisha", but not "K+K" as in "K+K Messtechnik".
    'limited',
    'llc',
    'ltd',
    'n ?v',
    'oao',
    'of',
    'open joint stock company',
    'ooo',
    'oü',
    'oy',
    'oyj',
    'plc',
    'pty',
    'pvt',
    's ?a ?r ?l',
    's ?a',
    's ?p ?a',
    'sp ?k',
    's ?r ?l',
    'systems',
    'the',
    'zao',
    'z ?o ?o',
    'technology',
    'technologies',
    'electronics',
    'communication',
    'communications',
    'telecommunications',
    'semiconductor',
    'device',
    ])

def shorten(manuf):
    '''Convert a long manufacturer name to abbreviated and short names'''
    # Normalize whitespace.
    manuf = ' '.join(manuf.split())
    orig_manuf = manuf
    # Add exactly one space on each end.
    # XXX This appears to be for the re.sub below.
    manuf = ' {} '.format(manuf)
    # Convert all caps to title case
    if manuf.isupper():
        manuf = manuf.title()
    # Remove any punctuation
    # XXX Use string.punctuation? Note that it includes '-' and '*'.
    manuf = re.sub(r"[\"',./:()]", ' ', manuf)
    # & isn't needed when Standalone
    manuf = manuf.replace(" & ", " ")
    # Remove business types and other general terms ("the", "inc", "plc", etc.)
    plain_manuf = re.sub(r'\W(' + general_terms + ')(?= )', '', manuf, flags=re.IGNORECASE)
    # ...but make sure we don't remove everything.
    if not all(s == ' ' for s in plain_manuf):
        manuf = plain_manuf
    manuf = ' '.join(manuf.split())
    # Remove all spaces
    # manuf = re.sub(r'\s+', ' ', manuf)

    if len(manuf) < 1:
        sys.stderr.write('Manufacturer "{}" shortened to nothing.\n'.format(orig_manuf))
        sys.exit(1)

    return manuf

def santize(manuf):
    '''Convert a long manufacturer name to abbreviated and short names'''
    # Normalize whitespace.
    manuf = ' '.join(manuf.split())
    orig_manuf = manuf
    # Add exactly one space on each end.
    # XXX This appears to be for the re.sub below.
    # manuf = ' {} '.format(manuf)
    # Remove any punctuation
    # XXX Use string.punctuation? Note that it includes '-' and '*'.
    manuf = re.sub(r"[\"']", ' ', manuf)

    return manuf

def prefix_to_oui(prefix):
    return prefix
    pfx_len = len(prefix) * 8 / 2

    if pfx_len == 24:
        # 24-bit OUI assignment, no mask
        return ''.join(hi + lo for hi, lo in zip(prefix[0::2], prefix[1::2]))

    # Other lengths which require a mask.
    #oui = prefix.ljust(len(prefix), '0')
    #oui = ''.join(hi + lo for hi, lo in zip(oui[0::2], oui[1::2]))
    return '{}/{:d}'.format(prefix, int(pfx_len))

def exec_rules(rules, name):
    for tup in rules:
        # print(tup)
        if tup[0].search(name):
            return tup
    #     print('{} does not match {}'.format(name, tup[0]))
    # print('{} does not match all'.format(name))

def main():
    this_dir = os.path.dirname(__file__)
    translate_path = os.path.join(this_dir, 'oui-translate.csv')
    # template_path = os.path.join(this_dir, '..', 'manuf.tmpl')
    header_l = []
    in_header = True

    ieee_d = {
        'OUI':   { 'url': "/oui/oui.csv", 'min_entries': 1000 },
        'CID':   { 'url': "/cid/cid.csv", 'min_entries': 75 },
        'IAB':   { 'url': "/iab/iab.csv", 'min_entries': 1000 },
        'OUI28': { 'url': "/oui28/mam.csv", 'min_entries': 1000 },
        'OUI36': { 'url': "/oui36/oui36.csv", 'min_entries': 1000 },
    }
    oui_d = {}
    oui_a = {}

    min_total = 35000; # 35830 as of 2018-09-05
    tmpl_added  = 0
    total_added = 0

    translate_fd = io.open(translate_path, 'r', encoding='UTF-8')
    translate_csv = csv.reader(translate_fd.readlines())
    next(translate_csv)
    translate_rules = list(map(lambda translate_row: (re.compile('^'+translate_row[0].replace('%', '.*')+'$', flags=re.IGNORECASE), translate_row[1], translate_row[2]), translate_csv))
    translate_fd.close()

    # Add IEEE entries from each of their databases
    ieee_db_l = list(ieee_d.keys())
    ieee_db_l.sort()

    for db in ieee_db_l:
        db_url = ieee_d[db]['url']
        ieee_d[db]['skipped'] = 0
        ieee_d[db]['added'] = 0
        ieee_d[db]['total'] = 0
        print('Merging {} data from {}'.format(db, db_url))
        (body, response_d) = open_url(db_url)
        ieee_csv = csv.reader(body.splitlines())
        ieee_d[db]['last-modified'] = "" # response_d['Last-Modified']
        ieee_d[db]['length'] = "" # response_d['Content-Length']

        # Pop the title row.
        next(ieee_csv)
        for ieee_row in ieee_csv:
            #Registry,Assignment,Organization Name,Organization Address
            #IAB,0050C2DD6,Transas Marine Limited,Datavagen 37 Askim Vastra Gotaland SE 436 32
            oui = prefix_to_oui(ieee_row[1].upper())
            manuf = ieee_row[2].strip()
            # The Organization Name field occasionally contains HTML entities. Undo them.
            manuf = html.unescape(manuf)
            if oui in oui_d:
                action = 'Skipping'
                try:
                    manuf_stripped = re.findall('[a-z]+', manuf.lower())
                    tmpl_manuf_stripped = re.findall('[a-z]+', oui_d[oui].split('\t')[-1].strip().lower())
                    if manuf_stripped == tmpl_manuf_stripped:
                        action = 'Skipping duplicate'
                except IndexError:
                    pass

                print('{} - {} IEEE "{}" in favor of "{}"'.format(oui, action, manuf, oui_d[oui]))
                ieee_d[db]['skipped'] += 1
            elif manuf == "Private":
                print('{} - Skipping Private'.format(oui))
                ieee_d[db]['skipped'] += 1
            else:
                oui_d[oui] = shorten(manuf)
                address = html.unescape(ieee_row[3].strip())
                oui_a[oui] = santize(address)
                ieee_d[db]['added'] += 1
            ieee_d[db]['total'] += 1

        if ieee_d[db]['total'] < ieee_d[db]['min_entries']:
            exit_msg("Too few {} entries. Got {}, wanted {}".format(db, ieee_d[db]['total'], ieee_d[db]['min_entries']))
        total_added += ieee_d[db]['total']

    if total_added < min_total:
        exit_msg("Too few total entries ({})".format(total_added))

    manuf_path = os.path.join(this_dir, 'dist', 'oui.csv')
    # Write the output file.
    try:
        manuf_fd = io.open(manuf_path, 'w', encoding='UTF-8')
    except Exception:
        exit_msg("Couldn't open manuf file for write ({}) ".format(manuf_path))

    oui_l = list(oui_d.keys())
    oui_l.sort()
    #manuf_fd.write('{\n')
    for oui in oui_l:
        if oui_d[oui] != "Private":
            tup = exec_rules(translate_rules, oui_d[oui])
            if tup:
                manuf_fd.write('{}\t{}\n'.format(oui, tup[1]))
    #manuf_fd.write('"FFFFFF":""\n}\n')
    manuf_fd.close()

    translate_rules.sort(key=lambda tup:tup[1].lower())
    cname_path = os.path.join(this_dir, 'dist', 'oui_cn.json')
    # Write the output file.
    try:
        cname_fd = io.open(cname_path, 'w', encoding='UTF-8')
    except Exception:
        exit_msg("Couldn't open cname file for write ({}) ".format(cname_path))

    cname_fd.write('{\n')
    en = {}
    for tup in translate_rules:
        if not tup[1] in en:
            en[tup[1]] = tup[2]
            cname_fd.write('"{}":"{}",\n'.format(tup[1], tup[2]))
    cname_fd.write('"":""\n}\n')
    cname_fd.close()

    print('{:<20}: {}'.format('Original entries', tmpl_added))
    for db in ieee_d:
        print('{:<20}: {}'.format('IEEE ' + db + ' added', ieee_d[db]['added']))
    print('{:<20}: {}'.format('Total added', total_added))

    print()
    for db in ieee_d:
        print('{:<20}: {}'.format('IEEE ' + db + ' total', ieee_d[db]['total']))

    print()
    for db in ieee_d:
        print('{:<20}: {}'.format('IEEE ' + db + ' skipped', ieee_d[db]['skipped']))
    print()

if __name__ == '__main__':
    main()
