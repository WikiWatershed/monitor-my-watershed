# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from dataloaderinterface.models import SiteRegistration
from accounts.models import User
from django.db.models import Sum, Q
from operator import __or__ as OR

from functools import reduce

class Macroinvertebrate(models.Model):
    """
    :var: scientific_name: The scientific name for the macroinvertebrate (i.e. 'Ephemeroptera')
    :var: common_name: The common for the macroinvertebrate (i.e. 'mayflies')
    :var: family_of: Establishes an Order-Family one-to-many relationships. For example, in biological classification,
     Diptera is the order of all true flies and includes the families of Anthericidae, Chironomidae, Simuliidae, etc.,
     but all are macroinvertebrate.
    """
    class Meta:
        db_table = 'macroinvertebrate'

    scientific_name = models.CharField(max_length=255)
    # 'latin_name' is basically the same as 'scientific_name', but it
    # can be blank. This was added to resolve an issue with displaying
    # names on the website.
    latin_name = models.CharField(max_length=255, default='', blank=True)
    common_name = models.CharField(max_length=255, unique=True)
    family_of = models.ForeignKey('Macroinvertebrate',
                                  on_delete=models.CASCADE,
                                  null=True,
                                  blank=True,
                                  related_name='families')
    pollution_tolerance = models.FloatField(default=0)
    itis_serial_number = models.CharField(max_length=255, null=True, blank=True)
    url = models.CharField(max_length=255, null=True, blank=True)
    displayflag = models.BooleanField(default=True)
    display_order = models.FloatField(default=0)
    parent_name = models.CharField(max_length=255, default='')

    sens_group = models.ForeignKey('LeafPackSensitivityGroup', on_delete=models.CASCADE)

    """
    'sort_priority' is used to determine the order taxon appear on things like django forms. HIGHER values  
    of sort_priority should appear first, and LOWER values last
    """
    sort_priority = models.FloatField(default=0)

    @property
    def is_ept(self):
        return self.scientific_name.lower() in ['ephemeroptera', 'plecoptera', 'tricoptera']

    @property
    def display_name(self):
        return self.__str__()

    def __str__(self):
        if not len(self.latin_name):
            return '{0}'.format(self.common_name, self.latin_name)
        if not len(self.parent_name):
            return '{0} ({1})'.format(self.common_name, self.scientific_name)
        else:
            return '{0} ({1}, {2})'.format(self.common_name, self.parent_name, self.scientific_name)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.family_of is not None and len(self.families.all()):
            raise AttributeError("'{}' is a parent of another taxon and therefore cannot be a subcategory of '{}'".format(
                self.__str__(), self.family_of.__str__()
            ))

        if self.family_of and self.family_of.family_of is not None:
            raise AttributeError("'{}' is a subcategory of another taxon and therefore cannot be a parent of '{}'".format(
                self.family_of.__str__(), self.__str__()
            ))

        super(Macroinvertebrate, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                            update_fields=update_fields)


class LeafPack(models.Model):
    """
    Leaf pack data
    """
    class Meta:
        db_table = 'leafpack'

    site_registration = models.ForeignKey(SiteRegistration, on_delete=models.CASCADE)
    placement_date = models.DateField()
    retrieval_date = models.DateField()
    leafpack_placement_count = models.IntegerField()
    leafpack_retrieval_count = models.IntegerField()
    placement_air_temp = models.FloatField(blank=True, null=True)
    placement_water_temp = models.FloatField(blank=True, null=True)
    retrieval_air_temp = models.FloatField(blank=True, null=True)
    retrieval_water_temp = models.FloatField(blank=True, null=True)
    had_storm = models.NullBooleanField()
    had_flood = models.NullBooleanField()
    had_drought = models.NullBooleanField()
    storm_count = models.IntegerField(default=0)
    storm_precipitation = models.FloatField(default=0)
    types = models.ManyToManyField('LeafPackType')
    deployment_type = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def taxon_count(self):
        """
        Gets the total count of taxon for the entire leafpack experiement.

        :return: total taxon count.
        """
        queryset = LeafPackBug.objects.filter(leaf_pack=self)
        #taxon_counts = [lpg.bug_count - self.sub_taxon_count(lpg.bug) for lpg in queryset if lpg.bug.displayflag]
        taxon_counts = [lpg.bug_count for lpg in queryset if lpg.bug.displayflag]

        return sum(taxon_counts)

    def sub_taxon_count(self, parent_taxon):
        queryset = LeafPackBug.objects.filter(leaf_pack=self)
        sub_taxon_count = queryset.filter(bug__family_of=parent_taxon).aggregate(Sum('bug_count'))

        if sub_taxon_count['bug_count__sum'] is not None:
            return sub_taxon_count['bug_count__sum']

        return 0

    def percent_EPT(self):
        """
        :return: The ratio of Ephemeroptera, Placoptera, and Tricoptera taxon counts to the total taxon count
        """
        total = self.taxon_count()

        if total == 0:
            return 0

        ept_filter = reduce(OR, [Q(bug__scientific_name=name) for name in ['Ephemeroptera', 'Plecoptera', 'Trichoptera other than Hydropsychidae']])

        queryset = LeafPackBug.objects.filter(ept_filter, leaf_pack=self)

        aggregate = queryset.aggregate(Sum('bug_count'))

        ept_counts = aggregate.get('bug_count__sum', 0)

        return (float(ept_counts) / float(total)) * 100.0

    def biotic_index(self):
        """
        :return: the biotic index... yeeup.
        """
        leafpack_count = self.leafpack_retrieval_count

        if leafpack_count == 0:
            return 0

        count_avg_total = tolerance_avg_total = 0

        lpgs = LeafPackBug.objects.filter(leaf_pack=self)

        for lpg in lpgs:
            sub_taxon_count = 0
            sub_taxons = lpg.bug.families.all()

            for sub_taxon in sub_taxons:
                sub_lpg = LeafPackBug.objects.get(leaf_pack=self, bug=sub_taxon)
                sub_taxon_count += sub_lpg.bug_count

            count_avg = float(lpg.bug_count - sub_taxon_count) / float(leafpack_count)
            count_avg_total += count_avg
            tolerance_avg_total += (count_avg * lpg.bug.pollution_tolerance)

        if count_avg_total == 0:
            return 0

        return float(tolerance_avg_total) / float(count_avg_total)

    def water_quality(self, biotic_index=None):
        """
        :param biotic_index: The biotic_index. If biotic_index is None, the value is re-calculated.
        :return: A string representation of the water quality based on the biotic_index.
        """
        if not biotic_index:
            biotic_index = self.biotic_index()

        if biotic_index < 3.75:
            return 'Excellent - Organic pollution unlikely'
        elif 3.75 <= biotic_index < 5.0:
            return 'Good - Some organic pollution'
        elif 5.0 <= biotic_index < 6.5:
            return 'Fair - Substantial pollution likely'
        else:
            return 'Poor - Severe pollution likely'

    def PTI_score(self):
        """
        :return: the PTI_score...
        """
        lpgs = LeafPackBug.objects.filter(leaf_pack=self)

        score =0
        for lpg in lpgs:
            if lpg.bug_count > 0 and lpg.bug.displayflag:
                score += lpg.bug.sens_group.weightfactor
                #if lpg.bug.sens_group.id==1:
                #    score +=3
                #elif lpg.bug.sens_group.id ==2:
                #    score +=2
                #else:
                #    score +=1

        return score

    def PollutionToleranceIndexRating(self, PTI_score=None):
        """
        :param PTI_score: The PTI_score. If PTI_score is None, the value is re-calculated.
        :return: A string representation of the pollution tolerance Index based on the PTI_score.
        """
        if not PTI_score:
            PTI_score = self.PTI_score()

        if PTI_score >= 23:
            return 'Excellent - Organic pollution unlikely'
        elif 17 <= PTI_score < 23:
            return 'Good - Some organic pollution'
        elif 11 <= PTI_score < 17:
            return 'Fair - Substantial pollution likely'
        else:
            return 'Poor - Severe pollution likely'

class LeafPackBug(models.Model):
    """
    This model defines the many-to-many relationship between LeafPack and Macroinvertebrate models
    :var: leaf_pack: An instance of LeafPack
    :var: bug: An instance of Macroinvertebrate... 'bug' is easier to spell...
    :var: bug_count: The number of associated macroinvertebrate counted in the associated leaf pack
    """
    class Meta:
        db_table = 'leafpack_bug'

    leaf_pack = models.ForeignKey(LeafPack, on_delete=models.CASCADE)
    bug = models.ForeignKey(Macroinvertebrate, on_delete=models.CASCADE)
    bug_count = models.IntegerField(default=0)


class LeafPackType(models.Model):
    """
    A simple class to store a leaf pack type (i.e. beech, birch, elm, gum, maple, pine, etc.)
    """
    class Meta:
        db_table = 'leafpack_type'

    name = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name

class LeafPackSensitivityGroup(models.Model):
    
    #pollution sensitivity group
    
    class Meta:
        db_table ="leafpack_sensitivity_group"
    name = models.CharField(max_length=50, unique=True)
    weightfactor = models.IntegerField(default=0)

    def __str__(self):
        return self.name