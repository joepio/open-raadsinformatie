import bugsnag

from ocd_backend import celery_app
from ocd_backend.exceptions import SkipEnrichment
from ocd_backend.log import get_source_logger
from ocd_backend.utils.http import HttpRequestMixin
from ocd_backend.utils import json_encoder
from ocd_backend.utils.misc import iterate, get_sha1_hash, doc_type
from ocd_backend.models.serializers import JsonLDSerializer, JsonSerializer
from ocd_backend.models import PropertyValue

log = get_source_logger('enricher')


class BaseEnricher(celery_app.Task):
    """The base class that enrichers should inherit."""

    def run(self, *args, **kwargs):
        """Start enrichment of a single item.

        This method is called by the transformer or by another enricher
        and expects args to contain a transformed (and possibly enriched)
        item. Kwargs should contain the ``source_definition`` dict.

        :returns: the output of :py:meth:`~BaseEnricher.enrich_item`
        """

        self.source_definition = kwargs['source_definition']
        self.enricher_settings = kwargs['enricher_settings']

        for _, doc in iterate(args):
            try:
                for prop, value in doc.properties(props=True, rels=True):
                    try:
                        if not hasattr(value, 'enricher_task'):
                            continue
                    except AttributeError:
                        continue

                    self.enrich_item(value)

            except SkipEnrichment as e:
                bugsnag.notify(e, severity="info")
                log.info('Skipping %s, reason: %s'
                         % (self.__class__.__name__, e.message))
            except IOError as e:
                # In the case of an IOError, disk space or some other
                # serious problem might occur.
                bugsnag.notify(e, severity="error")
                log.critical(e)
            except Exception, e:
                bugsnag.notify(e, severity="warning")
                log.warning('Unexpected error: %s (%s), reason: %s'
                         % (self.__class__.__name__, e.__class__.__name__, e))

        return args

    def enrich_item(self, item):
        """Enriches a single item.

        This method should be implemented by the class that inherits
        from :class:`.BaseEnricher`. The method should modify or add
        attributes of the supplied item.

        :param item: the collection specific index representation of the
            item.
        :type item: object
        """
        raise NotImplementedError


class DummyEnricher(BaseEnricher):
    def enrich_item(self, item):
        log.info('Dummy enriching this now:')
        log.info(item.__dict__)
        log.info('Got these settings:')
        log.info(self.enricher_settings)
        return item


class ExternalEnricher(BaseEnricher, HttpRequestMixin):
    def _make_property_value(self, k, v, item):
        res = PropertyValue()
        res.generate_ori_identifier()
        res.had_primary_source = item.had_primary_source
        res.name = k
        res.value = v
        return res

    def enrich_item(self, item):
        body = JsonLDSerializer().serialize(item)
        result = None
        try:
            result = self.upload(self.enricher_settings['url'], body)
        except Exception as e:
            log.error(
                'Something unexpectedly went wrong uploading to %s: %s' % (
                    self.enricher_settings['url'], e,))
        if result is not None:
            log.info('Got the following result:')
            log.info(result)
            item.classifications = []
            for do_id, doc_classifications in result.iteritems():
                item.classifications = [
                    self._make_property_value(k, v, item) for k, v in doc_classifications.iteritems()]
        return item
