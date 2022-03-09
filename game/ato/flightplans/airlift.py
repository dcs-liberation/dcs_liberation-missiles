from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import TYPE_CHECKING, Type

from game.utils import feet
from .ibuilder import IBuilder
from .planningerror import PlanningError
from .standard import StandardFlightPlan
from .waypointbuilder import WaypointBuilder

if TYPE_CHECKING:
    from ..flight import Flight
    from ..flightwaypoint import FlightWaypoint


class Builder(IBuilder):
    def build(self) -> AirliftFlightPlan:
        cargo = self.flight.cargo
        if cargo is None:
            raise PlanningError(
                "Cannot plan transport mission for flight with no cargo."
            )

        altitude = feet(1500)
        altitude_is_agl = True

        builder = WaypointBuilder(self.flight, self.coalition)

        pickup = None
        nav_to_pickup = []
        if cargo.origin != self.flight.departure:
            pickup = builder.pickup(cargo.origin)
            nav_to_pickup = builder.nav_path(
                self.flight.departure.position,
                cargo.origin.position,
                altitude,
                altitude_is_agl,
            )

        return AirliftFlightPlan(
            flight=self.flight,
            departure=builder.takeoff(self.flight.departure),
            nav_to_pickup=nav_to_pickup,
            pickup=pickup,
            nav_to_drop_off=builder.nav_path(
                cargo.origin.position,
                cargo.next_stop.position,
                altitude,
                altitude_is_agl,
            ),
            drop_off=builder.drop_off(cargo.next_stop),
            nav_to_home=builder.nav_path(
                cargo.origin.position,
                self.flight.arrival.position,
                altitude,
                altitude_is_agl,
            ),
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
        )


class AirliftFlightPlan(StandardFlightPlan):
    def __init__(
        self,
        flight: Flight,
        departure: FlightWaypoint,
        nav_to_pickup: list[FlightWaypoint],
        pickup: FlightWaypoint | None,
        nav_to_drop_off: list[FlightWaypoint],
        drop_off: FlightWaypoint,
        nav_to_home: list[FlightWaypoint],
        arrival: FlightWaypoint,
        divert: FlightWaypoint | None,
        bullseye: FlightWaypoint,
    ) -> None:
        super().__init__(flight, departure, arrival, divert, bullseye)
        self.nav_to_pickup = nav_to_pickup
        self.pickup = pickup
        self.nav_to_drop_off = nav_to_drop_off
        self.drop_off = drop_off
        self.nav_to_home = nav_to_home

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield self.departure
        yield from self.nav_to_pickup
        if self.pickup:
            yield self.pickup
        yield from self.nav_to_drop_off
        yield self.drop_off
        yield from self.nav_to_home
        yield self.arrival
        if self.divert is not None:
            yield self.divert
        yield self.bullseye

    @property
    def tot_waypoint(self) -> FlightWaypoint | None:
        return self.drop_off

    def tot_for_waypoint(self, waypoint: FlightWaypoint) -> timedelta | None:
        # TOT planning isn't really useful for transports. They're behind the front
        # lines so no need to wait for escorts or for other missions to complete.
        return None

    def depart_time_for_waypoint(self, waypoint: FlightWaypoint) -> timedelta | None:
        return None

    @property
    def mission_departure_time(self) -> timedelta:
        return self.package.time_over_target
