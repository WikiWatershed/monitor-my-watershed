# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from dataloaderinterface.models import SiteRegistration
from accounts.models import User
from django.db.models import Sum, Q
from operator import __or__ as OR

from functools import reduce
