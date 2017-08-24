""" allows object style access for dictionaries """


class ObjectDict(dict):
    """ allows object style access for dictionaries """

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError('No such attribute: %s' % name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError('No such attribute: %s' % name)
