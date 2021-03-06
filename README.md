# edc_metadata

[![Build Status](https://travis-ci.org/clinicedc/edc-metadata.svg?branch=develop)](https://travis-ci.org/clinicedc/edc-metadata) [![Coverage Status](https://coveralls.io/repos/github/clinicedc/edc-metadata/badge.svg?branch=develop)](https://coveralls.io/github/clinicedc/edc-metadata?branch=develop)

`edc-metadata` puts a "metadata" layer on top of your data collection forms, namely CRFs and Requisitions. The "metadata" can be used on a data entry dashboard as is done by `edc_dashboard` or by a data manager to review the completion status of required forms.

Metadata is stored in two models, `CrfMetaData` and `RequisitionMetaData`. One metadata record is created per form per visit. Metadata for a visit is only created for the forms specified for that visit in the visit schedule.  

Metadata is created for each visit when the `visit` model is saved. `edc_metadata` reads from the `visit_schedule` to decide what CRF and REQUISITION metadata to create for a visit. (Note: See `edc_visit_schedule`)  

Metadata is guaranteed to exist for every form in every visit where the visit form has been completed.


## `metadata` model instances

Each  `metadata` model instance, `CrfMetadata` or `RequisitionMetadata`, is "owned" by some other CRF or REQUISITION model listed in the `visit_schedule`. 

`CrfMetadata` model instances are created for each CRF listed in the visit schedule. That is, if the visit schedule schedules a CRF for 5 different visits, 5 `CrfMetadata` model instances will eventually be created. Metadata model instances are created when the `visit` model for a timepoint is saved.

When you  `save` a CRF within a visit, the `entry_status` of the the metadata instance's it owns is updtaed from `REQUIRED` to `KEYED`.

The same applies to `RequisitionMetadata` for REQUISITIONS.   

### Entry status

By default the `entry_status` field attribute is set to `REQUIRED`. You can change the default per CRF to `NOT_REQUIRED` in your declaration in the visit schedule.  See `visit_schedule.crf`.

The same applies to REQUISITIONS.   


## `metadata_rules` manipulate `metadata` model instances

`metadata_rules` are declared to manipulate `metadata` model instances. The rules change the `entry_status` field attribute from `REQUIRED` to `NOT_REQUIRED` or visa-versa. 

If the owner of the metadata instance, the CRF or REQUISITION model instance, exists, the entry status is updtaed to `KEYED`and the `metadata_rules` targeting the metadata instance are ignored. 

"metadata rules" are run on each `save` of the visit and owner model instances.

If a value on some other form implies that your form should not be completed, your form's metadata "entry_status" will change from REQUIRED to NOT REQUIRED upon `save` of the other form.

Metadata is `updated` through a `post_save` signal that re-runs the metadata rules.


## `metadata_rules` access data through `edc_reference`

In order to de-couple the metadata rules from each owner model class, metadata rules access the field values for each model via `edc_reference` instead of directly.

Each owner model class refeenced by metadata rules must be declared with the `ReferenceModelMixin` and the fields list registered with `site_reference_configs` global. This applies to all owner models, `source_model` and `target_models`. 

See also `edc_reference`


### Getting started:

#### Models: Visit, Crfs and Requisitions

Let's prepare the models that will be used in the scheduled data collection. These models are your visit models, crf models and requisition models.

Your application also has one or more `Visit` models. Each visit model is declared with the `CreatesMetadataModelMixin`:

    class SubjectVisit(CreatesMetadataModelMixin, PreviousVisitMixin, VisitModelMixin,
                       RequiresConsentModelMixin, BaseUuidModel):
    
        appointment = models.OneToOneField(Appointment)
    
        class Meta(RequiresConsentModelMixin.Meta):
            app_label = 'example'

Your `Crf` models are declared with the `CrfModelMixin`:

    class CrfOne(CrfModelMixin, ReferenceModelMixin, BaseUuidModel):
    
        subject_visit = models.ForeignKey(SubjectVisit)
    
        f1 = models.CharField(max_length=10, default='erik')
        
        class Meta:
            app_label = 'example'
    
Your `Requisition` models are declared with the `RequisitionModelMixin`:

    class SubjectRequisition(RequisitionModelMixin, ReferenceModelMixin, BaseUuidModel):
    
        subject_visit = models.ForeignKey(SubjectVisit)
    
        f1 = models.CharField(max_length=10, default='erik')

        class Meta:
            app_label = 'example'

#### `metadata_rules`

`metadata_rules` manipulate the `entry_status` of `crf` and `requisition` metadata. Rule are registered to `site_metadata_rules` in `metadata_rules.py`. Place this file in the root of your app. Each app can have one `metadata_rules.py`.

#### autodiscover

AppConfig will `autodiscover` the rule files and print to the console whatever it finds:

     * checking for rule_groups ...
     * registered rule groups from application 'edc_example'

#### Inspect rule groups

Inspect rule groups from the site registry:

    >>> from edc_metadata.rules.site_metadata_rules import site_metadata_rules
        
    >>> for rule_groups in site_metadata_rules.registry.values():
    >>>    for rule_group in rule_groups:
    >>>        print(rule_group._meta.rules)
    
    (<edc_example.rule_groups.ExampleRuleGroup: crfs_male>, <edc_example.rule_groups.ExampleRuleGroup: crfs_female>)
    (<edc_example.rule_groups.ExampleRuleGroup2: bicycle>, <edc_example.rule_groups.ExampleRuleGroup2: car>)    
    
#### Writing RuleGroups

`Rules` are declared in a `RuleGroup`. The syntax is similar to the `django` model class. 

Let's start with an example from the perspective of the person entering subject data. On a dashboard there are 4 forms (models) to be completed. The "rule" is that if the subject is male, only the first two forms should be completed. If the subject is female, only the last two forms should be completed. So the metadata should show:

    Subject is Male:
    crf_one - REQUIRED, link to entry screen available
    crf_two - REQUIRED, link to entry screen available
    crf_three - NOT REQUIRED, link to entry screen not available
    crf_four - NOT REQUIRED, link to entry screen not available

    Subject is Female:
    crf_one - NOT REQUIRED
    crf_two - NOT REQUIRED
    crf_three - REQUIRED
    crf_four - REQUIRED

A `Rule` that changes the metadata if the subject is male would look like this:

    crfs_male = CrfRule(
        predicate=P('gender', 'eq', 'MALE'),
        consequence=REQUIRED,
        alternative=NOT_REQUIRED,
        target_models=['crfone', 'crftwo'])

The rule above has a `predicate` that evaluates to True or not. If `gender` is equal to `MALE` the consequence is `REQUIRED`, else `NOT_REQUIRED`. For this rule, for a MALE, the metadata `entry_status` for `crf_one` and `crf_two` will be updated to `REQUIRED`. For a FEMALE both will be set to `NOT_REQUIRED`.

Rules are declared as attributes of a RuleGroup much like fields in a `django` model:

    @register()
    class ExampleRuleGroup(CrfRuleGroup):
    
        crfs_male = CrfRule(
            predicate=P('gender', 'eq', 'MALE'),
            consequence=REQUIRED,
            alternative=NOT_REQUIRED,
            target_models=['crfone', 'crftwo'])
    
        crfs_female = CrfRule(
            predicate=P('gender', 'eq', FEMALE),
            consequence=REQUIRED,
            alternative=NOT_REQUIRED,
            target_models=['crfthree', 'crffour'])
    
        class Meta:
            app_label = 'edc_example'

Rule group class declarations are placed in file `metadata_rules.py` in the root of your application. They are registered in the order in which they appear in the file. All rule groups are available from the `site_metadata_rules` global.

#### More on Rules

The rule `consequence` and `alternative` except these values:
    
    from edc_metadata.constants import REQUIRED, NOT_REQUIRED
    from edc_metadata.rules.constants import DO_NOTHING

    * REQUIRED
    * NOT_REQUIRED
    * DO_NOTHING 

It is recommended to write the logic so that the `consequence` is REQUIRED if the `predicate` evaluates to  `True`.

In the examples above, the rule `predicate` can only access values that can be found on the subjects's current `visit` instance or `registered_subject` instance. If the value you need for the rule `predicate` is not on either of those instances, you can pass a `source_model`. With the `source_model` declared you would have these data available:

* current visit model instance
* registered subject (see `edc_registration`)
* source model instance for the current visit

Let's say the rules changes and instead of refering to `gender` (male/female) you wish to refer to the value field of `favorite_transport` on model `CrfTransport`. `favorite_transport` can be "car" or "bicycle". You want the first rule `predicate` to read as:

* "If `favorite_transport` is equal to `bicycle` then set the metadata `entry_status` for `crf_one` and `crf_two` to REQUIRED, if not, set both to NOT_REQUIRED" 

and the second to read as:

* "If `favorite_transport` is equal to `car` then set the metadata `entry_status` for `crf_three` and `crf_four` to REQUIRED, if not, set both to NOT_REQUIRED".

The field for car/bicycle, `favorite_transport` is on model `CrfTransport`. The RuleGroup might look like this: 

    @register()
    class ExampleRuleGroup(RuleGroup):
    
        bicycle = CrfRule(
            predicate=P('favorite_transport', 'eq', 'bicycle'),
            consequence=REQUIRED,
            alternative=NOT_REQUIRED,
            target_models=['crfone', 'crftwo'])
    
        car = CrfRule(
            predicate=P('favorite_transport', 'eq', car),
            consequence=REQUIRED,
            alternative=NOT_REQUIRED,
            target_models=['crfthree', 'crffour'])
    
        class Meta:
            app_label = 'edc_example'
            source_model = 'CrfTransport'

Note that `CrfTransport` is a `crf` model in the Edc. That is, it has a `foreign key` to the visit model. Internally the query will be constructed like this:
    
    # source model instance for the current visit 
    visit_attr = 'subject_visit'
    source_obj = CrfTansport.objects.get(**{visit_attr: visit}) 
    
    # queryset of source model for the current subject_identifier
    visit_attr = 'subject_visit'
    source_qs = CrfTansport.objects.filter(**{'{}__subject_identifier'.format(visit_attr): subject_identifier}) 
    
If the source model instance does not exist, the rules in the rule group will not run. 

If the target model instance exists, no rule can change it's metadata from KEYED. 

##### More Complex Rule Predicates

There are two provided classes for the rule `predicate`, `P` and `PF`. With `P` you can make simple rule predicates like those used in the examples above. All standard opertors can be used. For example:

    predicate = P('gender', 'eq', 'MALE')
    predicate = P('referral_datetime', 'is not', None)
    predicate = P('age', '<=', 64)

If the logic needs to a bit more complicated, the `PF` class allows you to pass a `lambda` function directly:

    predicate = PF('age', func=lambda x: True if x >= 18 and x <= 64 else False)

    predicate = PF('age', 'gender', func=lambda x, y: True if x >= 18 and x <= 64 and y == MALE else False)
    
If the logic needs to be more complicated than is recommended for a simple lambda, you can just pass a function. When writing your function just remember that the rule `predicate` must always evaluate to True or False. 

    def my_func(visit, registered_subject, source_obj, source_qs):
        if source_obj.married and registered_subject.gender == FEMALE:
            return True
        return False

    predicate = my_func


#### Rule Group Order

RuleGroups are evaluated in the order they are registered and the rules within each rule group are evaluated in the order they are declared on the RuleGroup.


#### Testing

Since the order in which rules run matters, it is essential to test the rules together. See `tests` for some examples. When writing tests it may be helpful to know the following:

* the standard Edc model configuration assumes you have consent->enrollment->appointments->visit->crfs and requisitions. 
* rules can be instected after boot up in the global registry `site_metadata_rules`.
* all rules are run when the visit  is saved.

#### More examples

See `edc_example` for working RuleGroups and how models are configured with the `edc_metadata` mixins. The `tests` in `edc_metadata.rules` use the rule group and model classes in `edc_example`. 


#### Notes on Edc 

The standard Edc model configuration assumes you have a data entry flow like this:

    consent->enrollment->appointment->visit (1000)->crfs and requisitions
                         appointment->visit (2000)->crfs and requisitions
                         appointment->visit (3000)->crfs and requisitions
                         appointment->visit (4000)->crfs and requisitions
                         ...
(You should also see the other dependencies, `edc_consent`, `edc_visit_schedule`, `edc_appointment`, `edc_visit_tracking`, `edc_metadata`, etc.)

#### Signals

In the `signals` file: 

visit model `post_save`:

* Metadata is created for a particular visit and visit code, e.g. 1000, when the `visit` model is saved for a subject and visit code using the default `entry_status` configured in the `visit_schedule`.
* Immediately after creating metadata, all rules for the `app_label` are run in order. The `app_label` is the `app_label` of the visit model.

crf or requisition model `post_save`:

* the metadata instance for the crf/requisition is updated and then all rules are run.

crf or requisition model `post_delete`:

* the metadata instance for the crf/requisition is reset to the default `entry_status` and then all rules are run.


### Changing visit_schedule name and/ or schedule name

If the visit_schedule_name or schedule_name changes, the existing metadata must be manually updated. For example;


    update edc_metadata_crfmetadata set visit_schedule_name='visit_schedule'
    where visit_schedule_name='old_visit_schedule;
    
    update edc_metadata_crfmetadata set schedule_name='schedule'
    where schedule_name='old_schedule;

    update edc_metadata_requisitionmetadata set visit_schedule_name='visit_schedule'
    where visit_schedule_name='old_visit_schedule;
    
    update edc_metadata_requisitionmetadata set schedule_name='schedule'
    where schedule_name='old_schedule;

You also need to update any existing enrollment and disenrollment model data. For example;

    update ambition_subject_enrollment set visit_schedule_name='visit_schedule'
    where visit_schedule_name='old_visit_schedule;

    update ambition_subject_enrollment set schedule_name='schedule'
    where schedule_name='old_schedule;

For any other table that use these fields:

    SELECT DISTINCT TABLE_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE COLUMN_NAME IN ('visit_schedule_name','schedule_name')
            AND TABLE_SCHEMA='edc';
            
A typical list of tables that need to be updated may look like this

    +------------------------------------------+
    | TABLE_NAME                               |
    +------------------------------------------+
    | ambition_subject_disenrollment           |
    | ambition_subject_enrollment              |
    | ambition_subject_historicaldisenrollment |
    | ambition_subject_historicalenrollment    |
    | ambition_subject_historicalsubjectvisit  |
    | ambition_subject_subjectvisit            |
    | edc_appointment_appointment              |
    | edc_appointment_historicalappointment    |
    | edc_metadata_crfmetadata                 |
    | edc_metadata_requisitionmetadata         |
    +------------------------------------------+

In the code you need to update where the visit_schedule or schedule are hard coded.
* visit schedule, schedule
* Meta attributes on the enrollment and disenrollment models.

    
