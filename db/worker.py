import sqlalchemy as sq
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, subqueryload

engine = create_engine('sqlite:///db.db')
Base = declarative_base()


class VkUserModel(Base):
    __tablename__ = 'vk_user'

    id = sq.Column(sq.INTEGER, primary_key=True)
    vk_id = sq.Column(sq.INTEGER)
    search_cache = relationship('SearchCacheModel', backref='vk_user')

    def __str__(self):
        return f'id:{self.id} | vk_id:{self.vk_id}'

    def __repr__(self):
        return self.__str__()


class SearchCacheModel(Base):
    __tablename__ = 'search_cache'

    id = sq.Column(sq.INTEGER, primary_key=True)
    id_vk_user = sq.Column(sq.INTEGER, sq.ForeignKey('vk_user.id'))
    searched_vk_user = sq.Column(sq.INTEGER)

    def __str__(self):
        return f'id:{self.id} | id_vk_user:{self.id_vk_user} | searched_vk_user: {self.searched_vk_user}'

    def __repr__(self):
        return self.__str__()


class DBWorker:

    def __init__(self):
        self.status = True
        try:
            Base.metadata.create_all(bind=engine)
            self.session = sessionmaker(bind=engine)()
        except:
            self.status = False

    def dedublicate_search(self, vk_id, data, count):
        try:
            current_user = self.session.query(VkUserModel).filter(VkUserModel.vk_id == vk_id).first()
            if not current_user:
                new_vk_user = VkUserModel(vk_id=vk_id)
                self.session.add(new_vk_user)
                self.session.commit()
                [self.session.add(SearchCacheModel(searched_vk_user=searched_pair['id'], id_vk_user=new_vk_user.id))
                 for searched_pair in data[:count]
                 ]
                self.session.commit()
                return data[:count]
            cached_vk_users = list(map(lambda user: user.searched_vk_user, current_user.search_cache))
            dedublicated_data = []
            for search_result in data:
                if search_result['id'] not in cached_vk_users:
                    self.session.add(SearchCacheModel(searched_vk_user=search_result['id'], id_vk_user=current_user.id))
                    dedublicated_data.append(search_result)
                    if len(dedublicated_data) == count:
                        self.session.commit()
                        return dedublicated_data
        except Exception:
            self.status = False
            dedublicated_data = data
        return dedublicated_data