from ocd_backend.items import BaseItem
from ocd_backend.models import *


class IbabsPersonItem(BaseItem):
    def get_rights(self):
        return u'undefined'

    def get_collection(self):
        return unicode(self.source_definition['index_name'])

    def get_object_model(self):
        source_defaults = {
            'source': 'ibabs',
            'source_id_key': 'identifier',
            'organization': self.source_definition['key'],
        }

        person = Person(self.original_item['UserId'], **source_defaults)
        person.name = self.original_item['Name']
        person.family_name = self.original_item['LastName']
        person.biography = self.original_item['AboutMe']
        person.email = self.original_item['Email']
        person.phone = self.original_item['Phone']

        municipality = Organization(self.source_definition['almanak_id'], **source_defaults)
        municipality.name = self.source_definition['sitename']
        municipality.merge(name=self.source_definition['sitename'])

        municipality_member = Membership(**source_defaults)
        municipality_member.organization = municipality
        # TODO: Setting member = person causes infinite recursion
        # municipality_member.member = person
        # FunctionName is often set to 'None' in the source, in that case we fall back to 'Member'
        if self.original_item['FunctionName'] == 'None':
            municipality_member.role = 'Member'
        else:
            municipality_member.role = self.original_item['FunctionName']

        person.member_of = [municipality_member]

        if self.original_item['PoliticalPartyId']:
            # Currently there is no way to merge parties from the Almanak with parties from ibabs because
            # they do not share any consistent identifiers, so new nodes will be created for parties that ibabs
            # persons are linked to. This causes ibabs sources that have persons to have duplicate party nodes.
            # These duplicate nodes are necessary to cover ibabs sources that have no persons, otherwise those
            # sources would not have any parties.
            party = Organization(self.original_item['PoliticalPartyId'], **source_defaults)
            party.name = self.original_item['PoliticalPartyName']

            party_member = Membership(**source_defaults)
            party_member.organization = party
            # TODO: Setting member = person causes infinite recursion
            # party_member.member = person
            party_member.role = 'Member'

            person.member_of.append(party_member)

        return person
