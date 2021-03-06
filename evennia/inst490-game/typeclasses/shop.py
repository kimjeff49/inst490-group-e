from evennia.utils import evmenu

def menunode_shopfront(caller):
    "This is the top-menu screen."

    shopname = caller.location.key
    wares = caller.location.db.storeroom.contents

    # Wares includes all items inside the storeroom, including the
    # door! Let's remove that from our for sale list.
    wares = [ware for ware in wares if ware.key.lower() != "door"]

    text = "*** Welcome to %s! ***\n" % shopname
    if wares:
        text += "   Things for sale (choose 1-%i to inspect);" \
                " quit to exit:" % len(wares)
    else:
        text += "   There is nothing for sale; quit to exit."

    options = []
    for ware in wares:
        # add an option for every ware in store
        options.append({"desc": "%s (%s)" %
                             (ware.key, ware.db.gold_value or 1),
                        "goto": "menunode_inspect_and_buy"})
    return text, options

def menunode_buy_ware_result(caller, raw_string, **kwargs):
    "This will be executed first when choosing to buy."
    if not raw_string.strip():
        return "menunode_shopfront"

    try:
        int(raw_string)
    except Exception as e:
        return None

    value = kwargs.get('value')
    ware = kwargs.get('ware')
    wealth = kwargs.get('wealth')

    if wealth >= value:
        rtext = "You pay %i and purchase %s!" % \
                     (value * int(raw_string), ware.key)
        caller.db.inventory["Budget"] -= value * int(raw_string)
        caller.db.inventory[ware.key] += int(raw_string)
    else:
        rtext = "You cannot afford %i for %s!" % \
                      (value, ware.key)
    caller.msg(rtext)
    return "menunode_shopfront"

def menunode_inspect_and_buy(caller, raw_string, **kwargs):
    "Sets up the buy menu screen."

    ware = kwargs.get('ware')

    text = "Enter amount or <return> to go back"

    if not ware:
        wares = caller.location.db.storeroom.contents
        # Don't forget, we will need to remove that pesky door again!
        wares = [ware for ware in wares if ware.key.lower() != "door"]

        iware = int(raw_string) - 1

        store = {}
        store['ware'] = wares[iware]
        store['value'] = store['ware'].db.gold_value or 1
        inventory = caller.get_inventory()
        store['wealth'] = inventory["Budget"] or 0

        options = {"key": "_default",
                    "goto": (menunode_buy_ware_result, store)}
    else:
        options = {"key": "_default",
                    "goto": (menunode_buy_ware_result, kwargs)}
    return text, options

from evennia import Command

class CmdBuy(Command):
    """
    Start to do some shopping

    Usage:
      buy
      shop
      browse

    This will allow you to browse the wares of the
    current shop and buy items you want.
    """
    key = "buy"
    aliases = ("shop", "browse")

    def func(self):
        "Starts the shop EvMenu instance"
        evmenu.EvMenu(self.caller,
                      "typeclasses.shop",
                      startnode="menunode_shopfront")

from evennia import CmdSet

class ShopCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdBuy())

from evennia import DefaultRoom, DefaultExit, DefaultObject
from evennia.utils.create import create_object

# class for our front shop room
class NPCShop(DefaultRoom):
    def at_object_creation(self):
        # we could also use add(ShopCmdSet, permanent=True)
        self.cmdset.add_default(ShopCmdSet)
        self.db.storeroom = None

# command to build a complete shop (the Command base class
# should already have been imported earlier in this file)
class CmdBuildShop(Command):
    """
    Build a new shop

    Usage:
        @buildshop shopname

    This will create a new NPCshop room
    as well as a linked store room (named
    simply <storename>-storage) for the
    wares on sale. The store room will be
    accessed through a locked door in
    the shop.
    """
    key = "@buildshop"
    locks = "cmd:perm(Builders)"
    help_category = "Builders"

    def func(self):
        "Create the shop rooms"
        if not self.args:
            self.msg("Usage: @buildshop <storename>")
            return
        # create the shop and storeroom
        shopname = self.args.strip()
        shop = create_object(NPCShop,
                             key=shopname,
                             location=None)
        storeroom = create_object(DefaultRoom,
                             key="%s-storage" % shopname,
                             location=None)
        shop.db.storeroom = storeroom
        # create a door between the two
        shop_exit = create_object(DefaultExit,
                                  key="back door",
                                  aliases=["storage", "store room"],
                                  location=shop,
                                  destination=storeroom)
        storeroom_exit = create_object(DefaultExit,
                                  key="door",
                                  location=storeroom,
                                  destination=shop)
        # make a key for accessing the store room
        storeroom_key_name = "%s-storekey" % shopname
        storeroom_key = create_object(DefaultObject,
                                       key=storeroom_key_name,
                                       location=shop)
        # only allow chars with this key to enter the store room
        shop_exit.locks.add("traverse:holds(%s)" % storeroom_key_name)

        # inform the builder about progress
        self.caller.msg("The shop %s was created!" % shop)
