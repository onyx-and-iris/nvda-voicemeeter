from pyparsing import Group, OneOrMore, Optional, Suppress, Word, alphanums, restOfLine


class Parser:
    def __init__(self):
        self.widget = Group(OneOrMore(Word(alphanums)))
        self.token = Suppress("||")
        self.identifier = Group(OneOrMore(Word(alphanums)))
        self.event = Group(OneOrMore(Word(alphanums)))
        self.match = self.widget + self.token + self.identifier + Optional(self.token) + Optional(self.event)
