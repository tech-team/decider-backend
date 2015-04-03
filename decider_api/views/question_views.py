import httplib
import json
from oauth2_provider.views import ProtectedResourceView
from decider_api.db.poll_items import get_poll_items
from decider_api.db.questions import tab_switch
from decider_api.utils.endpoint_decorators import require_post_data, require_get_params
from decider_app.models import Question, Category, User, Poll, PollItem
from decider_app.views.utils.response_builder import build_response, build_error_response
from decider_app.views.utils.response_codes import *


class QuestionsEndpoint(ProtectedResourceView):
    def get(self, request, *args, **kwargs):
        try:
            tab = request.GET.get('tab')
            limit = request.GET.get('limit')
            offset = request.GET.get('offset')

            errors = []
            if tab:
                try:
                    tab_func = tab_switch(tab.lower())
                    if tab_func is None:
                        return build_error_response(httplib.NOT_FOUND, CODE_UNKNOWN_TAB, "Tab is unknown")
                except TypeError:
                    return build_error_response(httplib.NOT_FOUND, CODE_UNKNOWN_TAB, "Tab is unknown")
            else:
                tab_func = tab_switch('new')

            if limit:
                try:
                    limit = int(limit)
                except ValueError:
                    errors.append('limit')
            if offset:
                try:
                    offset = int(offset)
                except ValueError:
                    errors.append('offset')

            if errors:
                return build_error_response(httplib.BAD_REQUEST, CODE_UNKNOWN_CATEGORY,
                                            "Some parameters are invalid", errors)

            question_list, q_columns = tab_func(user_id=request.resource_owner.id,
                                                limit=limit,
                                                offset=offset)
            questions = []
            polls = []
            for question_row in question_list:
                poll_id = question_row[q_columns.index('poll_id')]
                if poll_id:
                    polls.append(poll_id)

            poll_items_list, pi_columns = get_poll_items(polls)

            poll_items = {}
            for poll_item_row in poll_items_list:
                q_id = poll_item_row[pi_columns.index('question_id')]
                pi = {
                    'id': poll_item_row[pi_columns.index('id')],
                    'text': poll_item_row[pi_columns.index('text')],
                    'image_url': poll_item_row[pi_columns.index('image_url')],
                    'votes_count': poll_item_row[pi_columns.index('votes_count')]
                }

                if not poll_items.get(q_id):
                    poll_items[q_id] = []
                poll_items[q_id].append(pi)

            for question_row in question_list:
                question = {
                    'id': question_row[q_columns.index('id')],
                    'text': question_row[q_columns.index('text')],
                    'creation_date': question_row[q_columns.index('creation_date')],
                    'category_id': question_row[q_columns.index('category_id')],
                    'likes_count': question_row[q_columns.index('likes_count')],
                    'comments_count': question_row[q_columns.index('comments_count')],
                    'author': {
                        'id': question_row[q_columns.index('author_id')],
                        'username': question_row[q_columns.index('username')],
                        'first_name': question_row[q_columns.index('first_name')],
                        'last_name': question_row[q_columns.index('last_name')],
                        'middle_name': question_row[q_columns.index('middle_name')],
                        'avatar': question_row[q_columns.index('image_url')]
                    },
                    'poll': poll_items.get(question_row[q_columns.index('id')]),
                    'is_anonymous': question_row[q_columns.index('is_anonymous')]
                }

                questions.append(question)

            extra_fields = {'count': len(questions)}
            # TODO: format questions
            return build_response(httplib.OK, CODE_OK, "Successfully fetched questions",
                                  questions, extra_fields)

        except Exception as e:
            print(e.message)
            # TODO: write to log
            return build_error_response(httplib.BAD_REQUEST, CODE_INVALID_DATA, "Failed to list questions")

    @require_post_data(['text', 'poll', 'category_id'])
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.POST.get("data"))
            text = data.get("text")
            poll = data.get("poll")
            category_id = 0
            is_anonymous = data.get("is_anonymous") if data.get("is_anonymous") else False

            errors = []
            try:
                category_id = int(data.get("category_id"))
                if not category_id:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append("category_id")

            if errors:
                return build_error_response(httplib.BAD_REQUEST, CODE_UNKNOWN_CATEGORY,
                                            "Some fields are invalid", errors)

            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return build_error_response(httplib.NOT_FOUND, CODE_UNKNOWN_CATEGORY, "Category is unknown")

            question = Question.objects.create(text=text, category=category, is_anonymous=is_anonymous,
                                               author=request.resource_owner)
            question_poll = Poll.objects.create(question=question)

            data_poll = []
            for poll_item in poll:
                text = poll_item.get('text')
                # picture = ""
                # TODO: get image from poll_item.image

                if not text:
                    return build_error_response(httplib.BAD_REQUEST, CODE_UNKNOWN_CATEGORY,
                                                "Some fields are invalid", ["poll_item.text"])

                pi = PollItem.objects.create(poll=question_poll, question=question,
                                             text=poll_item['text'])  # TODO: picture
                data_poll.append({
                    'id': pi.id,
                    'text': pi.text,
                    # 'image_uid': pi.picture.uid
                    # TODO: picture
                })

            author = {
                "id": request.resource_owner.id,
                "username": request.resource_owner.username,
                "last_name": request.resource_owner.last_name,
                "first_name": request.resource_owner.first_name,
                # "avatar": request.resource_owner.avatar_url
                # TODO: avatar
            }

            data = {
                "id": question.id,
                "text": question.text,
                "creation_date": question.creation_date,
                "category_id": category.id,
                "author": author,
                "poll": data_poll,
                "is_anonymous": question.is_anonymous
            }

            return build_response(httplib.CREATED, CODE_CREATED, "Question added", data)
        except Exception as e:
            print(e)
            # TODO: write to log
            return build_error_response(httplib.BAD_REQUEST, CODE_INVALID_DATA, "Failed to create question")
