# -*- coding: utf-8 -*-
import re
import codecs
import json
# using etree rather than lxml here to reduce dependencies in core code
import xml.etree.ElementTree as etree


class Exporter(object):

    def export_data(self,
                    data,
                    format='positive_xml',
                    negative_apparatus=False,
                    ignore_basetext=False,
                    overlap_status_to_ignore=['overlapped', 'deleted'],
                    consolidate_om_verse=True,
                    consolidate_lac_verse=True,
                    include_lemma_when_no_variants=False):
        print('using core Exporter')
        print(overlap_status_to_ignore)
        print(format)
        output = []
        for unit in data:
            if format == 'negative_xml':
                negative_apparatus = True
            output.append(etree.tostring(self.get_unit_xml(unit,
                                                           ignore_basetext=ignore_basetext,
                                                           negative_apparatus=negative_apparatus,
                                                           overlap_status_to_ignore=overlap_status_to_ignore,
                                                           consolidate_om_verse=consolidate_om_verse,
                                                           consolidate_lac_verse=consolidate_lac_verse,
                                                           include_lemma_when_no_variants=include_lemma_when_no_variants
                                                           ), 'utf-8').decode())

        return '<?xml version="1.0" encoding="utf-8"?><TEI xmlns="http://www.tei-c.org/ns/1.0">{}' \
               '</TEI>'.format('\n'.join(output).replace('<?xml version=\'1.0\' encoding=\'utf-8\'?>', ''))

    def get_text(self, reading, type=None):
        if type == 'subreading':
            return [reading['text_string'].replace('&lt;', '<').replace('&gt;', '>')]
        if len(reading['text']) > 0:
            if 'text_string' in reading:
                return [reading['text_string'].replace('&lt;', '<').replace('&gt;', '>')]
            return [' '.join(i['interface'] for i in reading['text'])]
        else:
            if 'overlap_status' in reading.keys() and (reading['overlap_status'] in overlap_status_to_ignore):
                text = ['', reading['overlap_status']]
            # TODO: make sure this works for special category readings
            elif 'type' in reading.keys() and reading['type'] in ['om_verse', 'om']:
                if 'details' in reading.keys():
                    text = [reading['details'], reading['type']]
                else:
                    text = ['om', reading['type']]
            elif 'type' in reading.keys() and reading['type'] in ['lac_verse', 'lac']:
                if 'details' in reading.keys():
                    text = [reading['details'], reading['type']]
                else:
                    text = ['lac', reading['type']]
        return text

    def get_lemma_text(self, overtext, start, end):
        if start == end and start % 2 == 1:
            return ['', 'om']
        real_start = int(start/2)-1
        real_end = int(end/2)-1
        word_list = [x['original'] for x in overtext['tokens']]
        return [' '.join(word_list[real_start:real_end+1])]

    def get_witnesses(self, reading, missing):
        witnesses = ['{}{}'.format(x, reading['suffixes'][i]) for i, x in enumerate(reading['witnesses'])]
        for miss in missing:
            if miss in witnesses:
                witnesses.remove(miss)
        return witnesses

    def make_reading(self, reading, i, label, witnesses, type=None, subtype=None):
        rdg = etree.Element('rdg')
        rdg.set('n', label)
        text = self.get_text(reading, type)
        if type:
            rdg.set('type', type)
            if subtype:
                rdg.set('cause', subtype)
        elif len(text) > 1:
            rdg.set('type', text[1])
        rdg.text = text[0]
        pos = i+1
        rdg.set('varSeq', '{}'.format(pos))
        if len(witnesses) > 0:
            rdg.set('wit', ' '.join(witnesses))
            wit = etree.Element('wit')
            for witness in witnesses:
                idno = etree.Element('idno')
                idno.text = witness
                wit.append(idno)
            rdg.append(wit)
        return rdg

    def get_app_units(self,
                      apparatus,
                      overtext,
                      context,
                      missing,
                      negative_apparatus=False,
                      include_lemma_when_no_variants=False,
                      overlap_status_to_ignore=['overlapped', 'deleted']):
        app_list = []
        print('get_app_units')
        print(overlap_status_to_ignore)
        print(negative_apparatus)
        for unit in apparatus:
            start = unit['start']
            end = unit['end']
            app = etree.fromstring('<app type="main" n="%s" from="%s" to="%s"></app>' % (context, start, end))
            lem = etree.Element('lem')
            lem.set('wit', overtext['id'])
            text = self.get_lemma_text(overtext, int(start), int(end))
            lem.text = text[0]
            if len(text) > 1:
                lem.set('type', text[1])
            app.append(lem)
            readings = False
            if include_lemma_when_no_variants:
                readings = True
            for i, reading in enumerate(unit['readings']):
                wits = self.get_witnesses(reading, missing)
                if negative_apparatus is True:
                    if ((len(wits) > 0 or reading['label'] == 'a')
                            and ('overlap_status' not in reading
                                 or reading['overlap_status'] not in overlap_status_to_ignore)):
                        if reading['label'] == 'a':
                            wits = []
                        if len(wits) > 0:
                            readings = True
                        app.append(self.make_reading(reading, i, reading['label'], wits))
                    if 'subreadings' in reading:
                        for key in reading['subreadings']:
                            for subreading in reading['subreadings'][key]:
                                wits = self.get_witnesses(subreading, missing)
                                if len(wits) > 0:
                                    readings = True
                                    app.append(self.make_reading(subreading, i,
                                                                 '%s%s' % (reading['label'],
                                                                           subreading['suffix']),
                                                                 wits, 'subreading', key))

                else:
                    if ((len(wits) > 0 or reading['label'] == 'a')
                            and ('overlap_status' not in reading
                                 or reading['overlap_status'] not in overlap_status_to_ignore)):
                        if len(wits) > 0:
                            readings = True
                        app.append(self.make_reading(reading, i, reading['label'], wits))
                    if 'subreadings' in reading:
                        for key in reading['subreadings']:
                            for subreading in reading['subreadings'][key]:
                                wits = self.get_witnesses(subreading, missing)
                                if len(wits) > 0:
                                    readings = True
                                    app.append(self.make_reading(subreading, i,
                                                                 '%s%s' % (reading['label'],
                                                                           subreading['suffix']),
                                                                 wits, 'subreading', key))

            if readings:
                app_list.append(app)
        return app_list

    def get_unit_xml(self,
                     entry,
                     ignore_basetext=False,
                     negative_apparatus=False,
                     overlap_status_to_ignore=['overlapped', 'deleted'],
                     consolidate_om_verse=True,
                     consolidate_lac_verse=True,
                     include_lemma_when_no_variants=False):
        context = entry['context']
        basetext_siglum = entry['structure']['overtext'][0]['id']

        apparatus = entry['structure']['apparatus'][:]

        # make sure we append lines in order
        ordered_keys = []
        for key in entry['structure']:
            if re.match(r'apparatus\d+', key) is not None:
                ordered_keys.append(int(key.replace('apparatus', '')))
        ordered_keys.sort()

        for num in ordered_keys:
            apparatus.extend(entry['structure']['apparatus{}'.format(num)])

        vtree = etree.fromstring('<ab xml:id="{}-APP"></ab>'.format(context))
        # here deal with the whole verse lac and om and only use witnesses elsewhere not in these lists
        missing = []
        if consolidate_om_verse or consolidate_lac_verse:
            app = etree.fromstring('<app type="lac" n="{}">'
                                   '<lem wit="editorial">Whole verse</lem>'
                                   '</app>'.format(context))

            if consolidate_lac_verse:
                if len(entry['structure']['lac_readings']) > 0:
                    rdg = etree.Element('rdg')

                    rdg.set('type', 'lac')
                    rdg.text = 'Def.'
                    lac_witnesses = entry['structure']['lac_readings']
                    rdg.set('wit', ' '.join(lac_witnesses))
                    wit = etree.Element('wit')
                    for witness in lac_witnesses:
                        idno = etree.Element('idno')
                        idno.text = witness
                        wit.append(idno)
                    rdg.append(wit)
                    app.append(rdg)
                missing.extend(entry['structure']['lac_readings'])

            if consolidate_om_verse:
                if len(entry['structure']['om_readings']) > 0:
                    rdg = etree.Element('rdg')
                    rdg.set('type', 'lac')
                    rdg.text = 'Om.'
                    om_witnesses = entry['structure']['om_readings']
                    rdg.set('wit', ' '.join(om_witnesses))
                    wit = etree.Element('wit')
                    for witness in om_witnesses:
                        idno = etree.Element('idno')
                        idno.text = witness
                        wit.append(idno)
                    rdg.append(wit)
                    app.append(rdg)
                missing.extend(entry['structure']['om_readings'])

            vtree.append(app)

        # if we are ignoring the basetext add it to our missing list so it isn't listed (except n lemma)
        if ignore_basetext:
            missing.append(basetext_siglum)
        # this sort will change the order of the overlap units so longest starting at each index point comes first
        apparatus = sorted(apparatus, key=lambda d: (d['start'], -d['end']))
        optns = {'include_lemma_when_no_variants': include_lemma_when_no_variants,
                 'negative_apparatus': negative_apparatus,
                 'overlap_status_to_ignore': overlap_status_to_ignore
                 }
        app_units = self.get_app_units(apparatus, entry['structure']['overtext'][0], context, missing, **optns)
        for app in app_units:
            vtree.append(app)

        return vtree
