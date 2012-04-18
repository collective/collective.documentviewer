default_profile = 'profile-collective.documentviewer:default'


def upgrade_to_1_1(context):
    context.runImportStepFromProfile(default_profile, 'controlpanel')
