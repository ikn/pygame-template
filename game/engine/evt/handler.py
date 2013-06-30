"""An event handler, which stores events and passes Pygame events to them."""

import pygame as pg

from ..conf import conf
from . import inputs
from .evts import BaseEvent, Event
from . import conffile


class EventHandler (dict):
    """Handles events.

EventHandler(scheduler)

:arg scheduler: :class:`sched.Scheduler <engine.sched.Scheduler>` instance to
                use for determining the current framerate.

Call :meth:`update` every frame to process and progagate Pygame events and call
callbacks.

Some notes:

 - An event may be placed in a 'domain', which is represented by a string name.
 - Events are named or unnamed, and an :class:`EventHandler` is a ``dict`` of
   named events.
 - The ``'domain'`` name is reserved.
 - The ``__contains__`` method (``event in event_handler``) works for
   :class:`BaseEvent <engine.evt.evts.BaseEvent>` instances as well as names.

"""

    def __init__ (self, scheduler):
        #: As passed to the constructor.
        self.scheduler = scheduler
        #: A ``set`` of domains that will recieve relevant events.
        self.active_domains = set()
        #: A ``set`` of domains that have been disabled through
        #: :meth:`disable`.
        self.inactive_domains = set()
        self._evts_by_domain = {}
        #: A ``set`` of all registered unnamed events.
        self.evts = set()
        # all inputs registered with events, prefiltered by Input.filters
        self._filtered_inputs = ('type', {inputs.UNFILTERABLE: set()})
        # all registered modifiers
        self._mods = {}

    def __str__ (self):
        return '<EventHandler object at {0}>'.format(hex(id(self)))

    def __contains__ (self, item):
        return (dict.__contains__(self, item) or item in self.itervalues() or
                item in self.evts)

    def __setitem__ (self, item, val):
        self.add(**{item: val})

    def __delitem__ (self, item):
        self.rm(item)

    def add (self, *evts, **named_evts):
        """Register events.

add(*evts, **named_evts) -> unnamed

Arguments are any number of events.  Keyword arguments define named events with
the key as the name.  An event can be a
:class:`BaseEvent <engine.evt.evts.BaseEvent>` instance, or a sequence of
Pygame event IDs and functions to create an
:class:`BaseEvent <engine.evt.evts.BaseEvent>` that listens for the given
Pygame events and has the functions as callbacks.

:return: a list of added unnamed events (positional arguments) (possibly
         created in this call).

"""
        # NOTE: add(*evts, **named_evts, domain = None)
        # NOTE: can call with existing event to change domain
        new_unnamed = []
        unnamed = self.evts
        by_domain = self._evts_by_domain
        # extract domain from keyword args
        if 'domain' in named_evts:
            domain = named_evts['domain']
            if domain is not None and not isinstance(domain, basestring):
                raise ValueError('invalid domain (or, \'domain\' is an '
                                 'invalid event name)')
            del named_evts['domain']
        else:
            domain = None
        if domain not in by_domain:
            # domain doesn't exist yet
            by_domain[domain] = []
            if domain is not None:
                self.active_domains.add(domain)
        for evts in (((None, evt) for evt in evts), named_evts.iteritems()):
            for name, evt in evts:
                if not isinstance(evt, BaseEvent): # NOTE: also Scheme
                    # got (possibly mixed) list of pgevts/cbs: create event
                    pgevts = []
                    cbs = []
                    for item in evt:
                        (cbs if callable(item) else pgevts).append(item)
                    evt = Event(*(inputs.BasicInput(pgevt)
                                  for pgevt in pgevts)).cb(*cbs)
                if evt.eh is not None:
                    if evt.eh is self:
                        # already own this event
                        prev_domain = evt._domain
                        if domain != prev_domain:
                            # change registered domain
                            by_domain[prev_domain].remove(evt)
                            if not by_domain[prev_domain]:
                                del by_domain[prev_domain]
                            evt._domain = domain
                            by_domain[domain].append(evt)
                        prev_name = evt._regname
                        if name != prev_name:
                            # change registered name
                            if prev_name is None:
                                unnamed.remove(evt)
                            else:
                                dict.__delitem__(self, prev_name)
                            evt._regname = name
                            if name is None:
                                unnamed.add(evt)
                            else:
                                dict.__setitem__(self, name, evt)
                    else:
                        # owned by another handler
                        raise RuntimeError('an event should not be added to '
                                           'more than one EventHandler')
                else:
                    # new event
                    evt.eh = self
                    evt._changed = False
                    evt._domain = domain
                    evt._regname = name
                    by_domain[domain].append(evt)
                    if name is None:
                        unnamed.add(evt)
                        new_unnamed.append(evt)
                    else:
                        dict.__setitem__(self, name, evt)
                    self._add_inputs(*evt.inputs)
        return new_unnamed

    def rm (self, *evts):
        """Takes any number of registered event names or events to remove them.

Raises ``KeyError`` if any arguments are missing.

"""
        unnamed = self.evts
        by_domain = self._evts_by_domain
        active = self.active_domains
        inactive = self.inactive_domains
        for evt in evts:
            if isinstance(evt, basestring):
                # got name
                evt = self[evt] # raises KeyError
            if evt.eh is self:
                evt.eh = None
                domain = evt._domain
                by_domain[domain].remove(evt)
                if not by_domain[domain]:
                    del by_domain[domain]
                    if domain in active:
                        active.remove(domain)
                    else:
                        inactive.remove(domain)
                evt._domain = None
                if evt._regname is None:
                    unnamed.remove(evt)
                else:
                    dict.__delitem__(self, evt._regname)
                evt._regname = None
                self._rm_inputs(*evt.inputs)
            else:
                raise KeyError(evt)

    def _prefilter (self, filtered, filters, i):
        attr, filtered = filtered
        filters = dict(filters)
        # Input guarantees that this is non-empty
        vals = filters.pop(attr, (inputs.UNFILTERABLE,))
        for val in vals:
            if val in filtered:
                child = filtered[val]
            else:
                # create new branch
                filtered[val] = child = set()
            # add input to child
            if isinstance(child, tuple):
                self._prefilter(child, filters, i)
            else:
                # reached the end of a branch: child is a set of inputs
                if filters:
                    # create new levels for each remaining filter
                    for attr, vals in filters.iteritems():
                        child = (attr, {inputs.UNFILTERABLE: child})
                    filtered[val] = child
                    self._prefilter(child, filters, i)
                else:
                    child.add(i)

    def _unprefilter (self, filtered, filters, i):
        filters = dict(filters)
        attr, filtered = filtered
        # Input guarantees that this is non-empty
        vals = filters.pop(attr, (inputs.UNFILTERABLE,))
        for val in vals:
            assert val in filtered
            child = filtered[val]
            if isinstance(child, tuple):
                self._unprefilter(child, filters, i)
                child = child[1]
            else:
                # reached the end of a branch: child is a set of inputs
                assert i in child
                child.remove(i)
            if not child:
                # child is now empty
                if val is inputs.UNFILTERABLE:
                    # retain the UNFILTERABLE branch
                    filtered[val] = set()
                else:
                    del filtered[val]
        if attr != 'type' and not any(filtered.itervalues()):
            # all branches are empty (but always retain the 'type' branch)
            filtered.clear()

    def _add_inputs (self, *inps):
        mods = self._mods
        for i in inps:
            if isinstance(i, inputs.ButtonInput):
                # add mods, sorted by device and device ID
                for m in i.mods:
                    added = False
                    for device in inputs.mod_devices[i.device]:
                        this_mods = mods.setdefault(device, {}) \
                                        .setdefault(i._device_id, {})
                        if m in this_mods:
                            this_mods[m].add(i)
                            # already added as an input
                        else:
                            this_mods[m] = set((i,))
                            if not added:
                                added = True
                                self._add_inputs(m)
            self._prefilter(self._filtered_inputs, i.filters, i)

    def _rm_inputs (self, *inps):
        mods = self._mods
        for i in inps:
            if isinstance(i, inputs.ButtonInput):
                for m in i.mods:
                    rmd = False
                    for device in inputs.mod_devices[i.device]:
                        d1 = mods[device]
                        d2 = d1[i._device_id]
                        d3 = d2[m]
                        assert i in d3
                        d3.remove(i)
                        if not d3:
                            del d2[m]
                            if not rmd:
                                rmd = True
                                self._rm_inputs(m)
                            if not d2:
                                del d1[i._device_id]
                                if not d1:
                                    del mods[device]
            self._unprefilter(self._filtered_inputs, i.filters, i)

    def update (self):
        """Process Pygame events and call callbacks."""
        all_inputs = self._filtered_inputs
        mods = self._mods
        for pgevt in pg.event.get():
            # find matching inputs
            inps = all_inputs
            while isinstance(inps, tuple):
                attr, inps = inps
                val = getattr(pgevt, attr) if hasattr(pgevt, attr) \
                                           else inputs.UNFILTERABLE
                inps = inps[val if val is inputs.UNFILTERABLE or val in inps
                                else inputs.UNFILTERABLE]
            # check all modifiers are active
            for i in inps:
                args = ()
                if isinstance(i, inputs.ButtonInput):
                    is_mod = i.is_mod
                    if is_mod:
                        # mods have no mods, so always match
                        args = (True,)
                    else:
                        this_mods = i.mods

                        def check_mods ():
                            for device in inputs.mod_devices[i.device]:
                                for m in mods.get(device, {}).get(i.device_id,
                                                                  ()):
                                    # mod motches if it's the same button as
                                    # the input itself
                                    if m == i:
                                        yield True
                                    # or if it's held in exactly this input's
                                    # components
                                    if m in this_mods:
                                        # only have one component
                                        yield (m.held(i)[0] and
                                               m._held.count(True) == 1)
                                    else:
                                        yield not any(m._held)

                        args = (all(check_mods()),)
                else:
                    is_mod = False
                # careful: mods have no event
                if i.handle(pgevt, *args) and not is_mod:
                    for evt in i.evts:
                        evt._changed = True
        # call callbacks
        by_domain = self._evts_by_domain
        for domains in ((None,), self.active_domains):
            for domain in domains:
                if domain is not None or domain in by_domain:
                    for evt in by_domain[domain]:
                        changed = evt._changed
                        evt._changed = False
                        evt.respond(changed)

    def domains (self, *domains):
        """Get all events in the given domains.

domains(*domains) -> evts

:return: ``(unnamed, named)``---a list of unnamed events and ``{name: event}``
         for named events.

"""
        unnamed = []
        named = {}
        for domain in domains:
            if domain is None:
                raise KeyError(domain)
            items.extend(self._evts_by_domain[domain]) # raises KeyError
        return (unnamed, named)

    def load (self, filename, domain = None):
        """Load events from a configuration file (see
:mod:`conffile <engine.evt.conffile>`).

load(filename, domain = None) -> evts

:arg filename: a filename to load as the configuration file, under
              :data:`conf.EVT_DIR`.
:arg domain: domain to place loaded events in.

:return: ``{name: event}`` for loaded events.

"""
        # NOTE: doesn't add events used in schemes - they _only_ go in the scheme
        with open(conf.EVT_DIR + filename) as f:
            evts = conffile.parse(f)
        if 'domain' in evts:
            raise ValueError('\'domain\' may not be used as an event name')
        evts['domain'] = domain
        self.add(**evts)
        return evts

    def save (self, name, *domains):
        """Not implemented."""
        # save everything in the domains to file
        pass

    def load_s (self, s, *domains):
        """Not implemented."""
        pass

    def save_s (self, *domains):
        """Not implemented."""
        pass

    def unload (self, *domains):
        """Remove all events in the given domains.

unload(*domains) -> evts

:return: all removed events as ``(unnamed, named)``, like :meth:`domains`.

Raises ``KeyError`` if a domain is missing.

"""
        unnamed, named = self.domains(*domains) # raises KeyError
        # now all domains exist so we can safely make changes
        # this removes empty domains
        self.rm(*unnamed)
        self.rm(*named)
        return (unnamed, named)

    def disable (self, *domains):
        """Disable event handling in all of the given domains.

Missing or already disabled domains are ignored (a domain is missing if it is
empty).

"""
        active = self.active_domains
        inactive = self.inactive_domains
        for domain in domains:
            if domain in active:
                active.remove(domain)
                inactive.add(domain)

    def enable (self, *domains):
        """Re-enable event handling in all of the given domains.

Missing or already active domains are ignored.  Beware that state is preserved,
so buttons that were held when disabled remain held when enabled, no matter how
much time has passed, without sending a
:data:`DOWN <engine.evt.evts.bmode.DOWN>`.

"""
        # %% refer to it here
        active = self.active_domains
        inactive = self.inactive_domains
        for domain in domains:
            if domain in inactive:
                inactive.remove(domain)
                active.add(domain)

    def assign_devices (**devices):
        """Not implemented."""
        # takes {varname: device_ids}, device_ids False for none, True for all, id or list of ids
        pass

    def grab (self, cb, *types):
        """Not implemented."""
        # grabs next 'on'-type event from given devices/types and passes it to cb
        # types are device name or (device, type_name)
        pass

    def monitor_deadzones (self, *deadzones):
        """Not implemented."""
        # takes list of  (device, id, *args); do for all if none given
        pass

    def stop_monitor_deadzones (self):
        """Not implemented."""
        # returns {(device, id, *args): deadzone}, args is axis for pad
        # can register other deadzone events?
        pass

    def set_deadzones (self, deadzones):
        """Not implemented."""
        # takes stop_monitor_deadzones result
        pass
