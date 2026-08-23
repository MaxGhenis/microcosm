"""Observed US plan-sponsor firm population sources and artifact builder.

Public APIs live in the focused ``form5500``, ``osha_ita``, ``staging``,
``targets``, ``frame``, and ``artifact`` modules.  Keeping package import free
of eager re-exports lets the staging CLI reject missing or unauthenticated
bytes before importing calibration dependencies.
"""
