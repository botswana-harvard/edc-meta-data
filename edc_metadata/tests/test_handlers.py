from django.test import TestCase, tag

from edc_appointment.models import Appointment
from edc_visit_schedule import site_visit_schedules
from edc_visit_tracking.constants import SCHEDULED
from edc_reference.site import site_reference_configs
from edc_base import get_utcnow

from ..constants import REQUISITION, CRF
from ..models import CrfMetadata, RequisitionMetadata
from ..requisition import InvalidTargetPanel, TargetPanelNotScheduledForVisit
from ..requisition import RequisitionTargetHandler
from ..target_handler import TargetModelLookupError, TargetHandler
from ..target_handler import TargetModelNotScheduledForVisit
from .models import SubjectVisit, SubjectConsent
from .reference_configs import register_to_site_reference_configs
from .visit_schedule import visit_schedule


class TestHandlers(TestCase):

    def setUp(self):
        register_to_site_reference_configs()
        site_visit_schedules._registry = {}
        site_visit_schedules.loaded = False
        site_visit_schedules.register(visit_schedule)
        site_reference_configs.register_from_visit_schedule(
            site_visit_schedules, autodiscover=False)
        self.subject_identifier = '1111111'
        self.assertEqual(CrfMetadata.objects.all().count(), 0)
        self.assertEqual(RequisitionMetadata.objects.all().count(), 0)
        subject_consent = SubjectConsent.objects.create(
            subject_identifier=self.subject_identifier,
            consent_datetime=get_utcnow())
        _, self.schedule = site_visit_schedules.get_by_onschedule_model(
            'edc_metadata.onschedule')
        self.schedule.put_on_schedule(
            subject_identifier=self.subject_identifier,
            onschedule_datetime=subject_consent.consent_datetime)
        self.appointment = Appointment.objects.get(
            subject_identifier=self.subject_identifier,
            visit_code=self.schedule.visits.first.code)

    def test_requisition_handler_invalid_target_panel(self):
        visit_obj = SubjectVisit.objects.create(
            appointment=self.appointment, reason=SCHEDULED)
        self.assertRaises(
            InvalidTargetPanel,
            RequisitionTargetHandler,
            model='edc_metadata.subjectrequisition',
            visit=visit_obj,
            target_panel='blah',
            metadata_category=REQUISITION)

    def test_requisition_handler_target_panel_not_for_visit(self):
        visit_obj = SubjectVisit.objects.create(
            appointment=self.appointment, reason=SCHEDULED)
        self.assertRaises(
            TargetPanelNotScheduledForVisit,
            RequisitionTargetHandler,
            model='edc_metadata.subjectrequisition',
            visit=visit_obj,
            target_panel='seven',
            metadata_category=REQUISITION)

    def test_crf_handler_invalid_target_model(self):
        visit_obj = SubjectVisit.objects.create(
            appointment=self.appointment, reason=SCHEDULED)
        self.assertRaises(
            TargetModelLookupError,
            TargetHandler,
            model='edc_metadata.crfblah',
            visit=visit_obj,
            metadata_category=CRF)

    def test_crf_handler_target_model_not_for_visit(self):
        visit_obj = SubjectVisit.objects.create(
            appointment=self.appointment, reason=SCHEDULED)
        self.assertRaises(
            TargetModelNotScheduledForVisit,
            TargetHandler,
            model='edc_metadata.crfseven',
            visit=visit_obj,
            metadata_category=CRF)
