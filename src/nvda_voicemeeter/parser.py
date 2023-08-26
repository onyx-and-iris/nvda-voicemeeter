from pyparsing import Group, OneOrMore, Optional, Suppress, Word, alphanums, restOfLine


class Parser:
    def __init__(self):
        self.widget = Group(OneOrMore(Word(alphanums)))
        self.widget_token = Suppress("||")
        self.identifier = Group(OneOrMore(Word(alphanums)))
        self.event = Group(OneOrMore(Word(alphanums)))
        self.menu_token = Suppress("::")
        self.match = (
            self.widget + self.widget_token + self.identifier + Optional(self.widget_token) + Optional(self.event)
            | self.identifier + self.menu_token + self.event
            | restOfLine
        )
