# -*- coding: utf-8 -*-
# This is blatantly copied from
# https://github.com/rgammans/MysteryMachine/blob/master/MysteryMachine/schema/MMListAttribute.py


class CharSortKey(object):
    """
    Encodes the actually logic used for generating dict keys for
    our ordered list.
    """
    """
    This class uses a tree analogy to create sortable strings for
    our dict elements.
    On each subtree self.order[0] and self.order[-1] are reserved to
    be immediately extended creating a new subtree
    Under normal circumstances we try to bisect the difference between the
    end (self.order[-1] in the case of append) and the start items.
    However if the two elements are 'adajenct' we create another subtree
    (append another character) and start from the center there.
    eg. (using a,b,c,d,e) as our symbols. 'a' and 'e' are reserved as
        our endpoints. and we start with 'c'

        append           -> c
                            c
        append           -> c , d
                            c--d
        insert(c)        -> c , cc ,d
                       c--d
                       |
                       cc
        insert(c)        -> c, cb , cc, d
                       c--+--d
                       |
                    cb-+-cc
        insert(c)        -> c , cac,cb,cc,d
                       c--+--d
                       |
                 (ca)-cb-+-cc
                  |
                 cac
    Note: We can't use the ca node as it is impossible to insert anything
          between the 'c' node and the 'ca' node.
    """
    #This _must_ be longer than three elements, otherwise the algorythm
    # cant always guarantee to find a between. Ideally it should be 3**n .
    #But I've compromised on 26 - one short of the ideal for n=3, becuase a-z
    # have a stable sort order across most (hopefully all) locales.
    order = [  ]
    for i in range(26):
        order.append(chr(ord('a') + i))

    #VV ---  Simple to trick to ensure algo requiremnt is true --- VV
    order = sorted(order)
    ##################################################################

    def __init__(self,value = None):
        self.abet =  self.__class__.order
        self.value = value
        if self.value is None:
            self.value = ''

    def __str__(self):
        return self.value

    def between(self,other):
        """
        Return a key half way between this and other - assuming no other
        intermediate keys exist in the tree.
        """
        ans = []
        for lo,hi in zip_longest(self.value,other):

            if lo is None: lo = self.abet[0]
            if hi is None: hi = self.abet[-1]

            if lo == hi:
                #The nodes are on the same subtree - so the answer will be too.
                ans.append(lo)
            else:
                #At this point we have found a difference between the subtrees which
                #contain the nodes.
                #But consider:-
                #           -b---------d-
                #            |         |
                #        bb--bc--bd    dc-dd
                #
                # I think it is sensible to return 'c' for insert_after('bd')
                new = self.abet[ ( self.abet.index(hi) +
                                   self.abet.index(lo) ) //2 ]

                #Check is unique and not reserved.
                if hi != new and lo != new and new !=0 and new != len(self.abet)-1:
                    ans.append(new)
                else:
                    #New subtree - ensure goes in a good place new == hi is the
                    #              only possible problem so lets trap it.
                    #      (It shouldn't occur due to integer division but..)
                    if new == hi: new=lo
                    ans += [ new , self.abet[len(self.abet) // 2] ]

                break

        return self.__class__("".join(ans))

    def next(self):
        """
        The implicit assumption is that this is the last key in the squenence.

        We need to return another key somewhere later in the sequence. We could
        use between() here but that wouldn't make the most use of the end element.

        So we use a slightly customized algorithm to do between(self,self.abet[-1])
        """

        if self.value == '':
            #Special case to handle empty string
            return self.__class__(self.abet[len(self.abet) // 2])

        ans = [ ]
        got = False
        for digit in self.value:
            if digit != self.abet[-1]:
                # Find digit 1/2 to the end rounding up (allowing us to use the end node)
                new = self.abet[ ( self.abet.index(digit) +
                                   len(self.abet)-1 )  // 2 ]

                #Run out of space on this subtree/node
                if new == digit:
                    # Last node on tree: -
                    #   use Create mid point in new subtree
                    ans += [self.abet[-1] , self.abet[len(self.abet) // 2] ]
                else:
                    ans += [ new ]
                #No need to add any more subtrees - so exit here.
                got = True
                break
            else:
                #On an end subtree move down and consider it alone...
                ans += [ digit ]

        #We must have finished succesfully as got can only be false if
        # if we have an unbroken sequenence of self.abet[-1]'s but we
        # never generate such a sequence.
        assert(got)
        return self.__class__("".join(ans))
