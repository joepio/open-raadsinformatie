from ocd_backend.items import BaseItem
from ocd_backend.models import *


class CommitteeItem(BaseItem):
    def get_rights(self):
        return u'undefined'

    def get_collection(self):
        return unicode(self.source_definition['index_name'])

    def get_object_model(self):
        source_defaults = {
            'source': 'ibabs',
            'source_id_key': 'identifier',
            'organization': self.source_definition['index_name'],
        }

        committee = Organization(self.original_item['Id'], **source_defaults)
        committee.name = self.original_item['Meetingtype']
        committee.description = self.original_item['Abbreviation']
        if 'sub' in self.original_item['Meetingtype']:
            committee.classification = u'Subcommittee'
        else:
            committee.classification = u'Committee'

        # Attach the committee node to the municipality node
        committee.subOrganizationOf = Organization(self.source_definition['key'], **source_defaults)
        committee.subOrganizationOf.merge(collection=self.source_definition['key'])

        return committee
