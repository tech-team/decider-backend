import httplib
from django.db import transaction
from oauth2_provider.views import ProtectedResourceView
from decider_api.db.vote import get_vote, insert_vote, delete_vote
from decider_api.log_manager import logger
from decider_api.utils.endpoint_decorators import require_registration, track_activity, require_params
from decider_app.views.utils.response_builder import build_error_response, build_response
from decider_app.views.utils.response_codes import CODE_INVALID_DATA, CODE_INVALID_ENTITY, CODE_CREATED, \
    I_CODE_ALREADY_VOTED, I_CODE_UNKNOWN_ENTITY, CODE_UNKNOWN_ENTITY


VOTE_ENTITIES = ['question', 'comment']


class VoteEndpoint(ProtectedResourceView):

    @transaction.atomic
    @track_activity
    @require_params(['entity', 'entity_id'])
    @require_registration
    def post(self, request, *args, **kwargs):
        try:
            entity = request.POST.get('entity')
            entity_id = request.POST.get('entity_id')

            if entity not in VOTE_ENTITIES:
                return build_error_response(httplib.BAD_REQUEST, CODE_INVALID_ENTITY,
                                            "Invalid entity")

            res, likes = get_vote(entity, entity_id, request.resource_owner.id)
            if res == I_CODE_UNKNOWN_ENTITY:
                return build_error_response(httplib.NOT_FOUND, CODE_UNKNOWN_ENTITY,
                                            msg="Unknown entity")

            already_voted = True if res == I_CODE_ALREADY_VOTED else False

            if already_voted:
                likes = delete_vote(entity, entity_id, request.resource_owner.id)
            else:
                likes = insert_vote(entity, entity_id, request.resource_owner.id)

            return build_response(httplib.CREATED, CODE_CREATED,
                                  msg="Vote successful",  data={'voted': not already_voted,
                                                                'entity_id': entity_id,
                                                                'likes_count': likes[0]})

        except Exception as e:
            logger.exception(e)
            return build_error_response(httplib.BAD_REQUEST, CODE_INVALID_DATA, "Failed to vote")
