from conf import VK_COMMUNITY_TOKEN_FULL, VK_APP_ID
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from random import randrange
from datetime import datetime
import json
from db.worker import DBWorker


class VKinder:
    __EP_SEND_MESSAGE = 'messages.send'

    __api_version = '5.131'
    __vk_url = 'https://vk.com/id'

    CMD_GET_PEOPLE = 10

    # CMD_LIKEPHOTO = 20

    CMD_SETUSERTOKEN = 40

    def __init__(self):
        self.__token_group = VK_COMMUNITY_TOKEN_FULL
        self.__application_id = VK_APP_ID
        self.__auth_url = f'https://oauth.vk.com/authorize?client_id={self.__application_id}&display=page&scope' \
                          f'=stats,offline,friends,groups,photos&response_type=token&v=5.131 '
        self.__user_token = None

        self.__vk_bot = vk_api.VkApi(token=self.__token_group, api_version=self.__api_version)
        self.__longpoll = VkLongPoll(self.__vk_bot)

        self.vk_requester = None

        self.__commands = {
            'set_token': (self.CMD_SETUSERTOKEN, self.__set_user_token),
            'find_pairs': (self.CMD_GET_PEOPLE, self.__get_pairs)
        }
        # 'like': (self.CMD_LIKEPHOTO, self.__like_photo
        self.__db_worker = DBWorker()

    def __set_user_token(self, **kwargs) -> list:
        self.__user_token = kwargs['params'][0]
        # print(self.__user_token)
        self.vk_requester = vk_api.VkApi(token=self.__user_token).get_api()
        return [{'msg': 'Token установлен'}]

    def __check_subject_user_is_unique(self, **kwargs):
        if kwargs['params'] and not kwargs['params'][0].isdigit():
            subject_user_id = self.__search_user({'q': kwargs['params'][0]}, strict_mode=True)['id']
            if not subject_user_id:
                return False, []
        elif kwargs['params']:
            return True, kwargs['params'][0]
        return True, kwargs['user_id']

    def __deduplicate_results(self, user, user_id, age, count, age_offeser, search_count):
        dedublicated_result = []

        while len(dedublicated_result) < count:
            pairs = self.__search_user({
                'city': user['city']['id'],
                'sex': (lambda x: 1 if x == 2 else 2)(user['sex']),
                'country': user['country']['id'],
                'relation': 1,
                'age_from': age - age_offeser,
                'age_to': age,
                'count': search_count,
                'fields': ('sex',),
                'has_photo': 1,
            })

            no_closed_result = [
                person
                for person in pairs['items']
                if person['can_access_closed'] == 1
            ]

            if self.__db_worker.status:

                dedublicated_result += self.__db_worker.dedublicate_search(vk_id=user_id,
                                                                           data=no_closed_result,
                                                                           count=count - len(
                                                                               dedublicated_result))
            else:
                dedublicated_result = no_closed_result

            search_count += count
        return dedublicated_result

    def __get_pairs(self, **kwargs) -> list:
        search_age_offset = 10
        result_count = 3
        search_count = 10

        check_status, subject_user_id = self.__check_subject_user_is_unique(**kwargs)

        if not check_status:
            return ['Найдено несколько пользователей, уточните запрос']

        subject_user = self.__get_user(subject_user_id)[0]

        subject_user_bdate = datetime.strptime(subject_user['bdate'], '%d.%m.%Y')
        subject_user_age = datetime.now().year - subject_user_bdate.year
        dedublicated_result = self.__deduplicate_results(user=subject_user,
                                                         user_id=subject_user_id,
                                                         age=subject_user_age,
                                                         count=result_count,
                                                         age_offeser=search_age_offset,
                                                         search_count=search_count)


        for p in dedublicated_result:
            p['preview_photo'] = self.__get_most_popular_photos(p['id'])

        result = [
            {
                'msg': f'{person["last_name"]} {person["first_name"]}:<br>{self.__vk_url}{person["id"]}',
                'photos': [
                    {
                        'url': photo['url'],
                        'attachment_id': photo['composed_id']
                    }
                    for photo in person['preview_photo']
                ],
            }
            for person in dedublicated_result
        ]

        return result

    def __get_most_popular_photos(self, user_id) -> list:
        result = []
        all_photos = self.vk_requester.photos.getAll(owner_id=user_id, count=5)['items']
        for photo in all_photos:
            photo_extended = self.vk_requester.photos.getById(photos=f'{photo["owner_id"]}_{photo["id"]}', extended=1)[
                0]
            result.append({
                'url': photo_extended['sizes'][len(photo_extended['sizes']) - 1]['url'],
                'sort_weight': photo_extended['likes']['count'] + photo_extended['comments']['count'],
                'composed_id': f'{photo["owner_id"]}_{photo["id"]}'
            })
        result = sorted(result, key=lambda x: x['sort_weight'])[:3]
        return result

    def __search_user(self, query, strict_mode=False) -> dict:
        if strict_mode:
            search_result = self.vk_requester.search.getHints(**query)
            if search_result.get('count') and search_result['count'] == 1:
                return search_result['items'][0]['profile']
            else:
                return {}
        else:
            search_result = self.vk_requester.users.search(**query)
            return search_result

    def __get_user(self, id) -> dict:
        user_data = self.vk_requester.users.get(
            user_ids=id,
            fields=('city', 'country', 'sex', 'bdate', 'relation')
        )
        return user_data

    def __route(self, **kwargs) -> list:
        if self.__user_token is None and (
                self.__commands[kwargs['command']][0] == self.CMD_SETUSERTOKEN and not kwargs.get('params')):
            return [{
                'msg': f'Не указан персональный токен, для этого перейдите по ссылке:<br>'
                       f'{self.__auth_url}<br>'
                       f'После чего скопируйте токен из адресной строки и введите комманду:<br>'
                       f'set_token <TOKEN>'}
            ]
        return self.__commands[kwargs['command']][1](**kwargs)

    # def __like_photo(self, **kwargs):
    #     if kwargs.get('payload'):
    #         payload = json.loads(kwargs['payload'])
    #         owner_id, item_id = payload['attachment_id'].split('_')
    #         # obj_type = 'photo'
    #         self.vk_requester.likes.add(type='photo', owner_id=owner_id, item_id=item_id)
    #         return [{'msg': 'Liked!'}]
    #     return [{'msg': 'Неверный формат комманды like'}]

    def start(self):
        for event in self.__longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                command, params = self.__read_command(event.text)
                command_response_list = [{'msg': 'Неверный формат команды! \n-------------\nДоступные команды: '
                                                 '\nset_token <TOKEN> - '
                                                 'установить токен \nfind_pairs - найти пару \n'}]
                if command in self.__commands.keys():

                    if self.__commands[command][0] == self.CMD_GET_PEOPLE:
                        self.__vk_bot.method(self.__EP_SEND_MESSAGE,
                                             {
                                                 'message': '<br>Начало поиска... это может занять некотрое время...<br><br>',
                                                 'user_id': event.user_id,
                                                 'random_id': randrange(10 ** 7)
                                             })
                    command_response_list = self.__route(command=command,
                                                         params=params,
                                                         user_id=event.user_id,
                                                         payload=event.extra_values.get('payload'))

                for line in command_response_list:
                    self.__vk_bot.method(self.__EP_SEND_MESSAGE,
                                         {'message': line['msg'], 'user_id': event.user_id,
                                          'random_id': randrange(10 ** 7), })
                    if command in self.__commands.keys() and self.__commands[command][0] == self.CMD_GET_PEOPLE:
                        carousel = {
                            "type": "carousel",
                            "elements": []
                        }

                        for photo in line['photos']:
                            carousel['elements'].append(
                                {
                                    "photo_id": "photo" + photo['attachment_id'],
                                    "action": {
                                        "type": "open_photo"
                                    },
                                    "buttons": [{
                                        "action": {
                                            "type": "text",
                                            "label": "like",
                                            "payload": {"attachment_id": photo['attachment_id']}
                                        }
                                    }]
                                }
                            )

                            self.__vk_bot.method(self.__EP_SEND_MESSAGE,
                                                 {'user_id': event.user_id,
                                                  'random_id': randrange(10 ** 7),
                                                  'attachment': f'photo{photo["attachment_id"]}'})
                            keyboard = json.dumps(dict(inline=True, buttons=[
                                [
                                    {
                                        "action": {
                                            "type": "text",
                                            "payload": "{\"attachment_id\": \"" + photo['attachment_id'] + "\"}"
                                        },
                                        "color": "primary"
                                    },
                                ]
                            ]))
                            self.__vk_bot.method(self.__EP_SEND_MESSAGE,
                                                 {'user_id': event.user_id,
                                                  'message': '-',
                                                  'random_id': randrange(10 ** 7)
                                                  })

                    self.__vk_bot.method(self.__EP_SEND_MESSAGE,
                                         {'message': f'<br>', 'user_id': event.user_id,
                                          'random_id': randrange(10 ** 7)})

    def __read_command(self, text_line):
        params = None
        split_text = text_line.split(' ')
        command = split_text[0]
        if len(split_text) > 1:
            params = split_text[1:]
        # print(command, params)
        return command, params
