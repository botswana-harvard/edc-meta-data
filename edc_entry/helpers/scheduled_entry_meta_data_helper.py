from ..models import Entry, ScheduledEntryMetaData

from .base_meta_data_helper import BaseMetaDataHelper


class ScheduledEntryMetaDataHelper(BaseMetaDataHelper):

    meta_data_model = ScheduledEntryMetaData
    entry_model = Entry
    entry_attr = 'edc_entry'
