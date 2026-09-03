from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import TEXT

from atguigu.repository.base import Base


class DialogueRecord(Base):
    __tablename__ = "dialogue_states"

    sender_id:Mapped[str]=mapped_column("sender_id",primary_key=True) # Mapped:可以在ide中进行类型提示和自动补全，类型推断：自动推断数据库对应列的类型
    state_json:Mapped[str]=mapped_column("state_json",TEXT,nullable=False,default="{}")