import os
from decimal import Decimal as D
from . import exceptions
import json
import logging



module_dir = os.path.split(os.path.abspath(__file__))[0]

class Observation(object):
    def __init__(self,chart,weight,muac,age_in_months,sex,height,logger_name):
        self.logger =logging.getLogger(logger_name)

        self.chart=chart
        self.weight=weight
        self.muac=muac
        self.age_in_months=age_in_months
        self.sex=sex
        self.height=height

        self.table_chart = None
        self.table_age = None
        self.table_sex = None
        if self.chart in ['wfl', 'wfh']:
            if self.height in ['', ' ', None]:
                raise exceptions.InvalidMeasurement('no length or height')

    @property
    def rounded_height(self):
        correction=D('0.5') if D(self.height)>=D(0) else D('-0.5')
        rounded = int(D(self.height) / D('0.5') + correction) * D('0.5')
        if rounded.as_tuple().digits[-1] == 0:
            return D(int(rounded)).to_eng_string()
        return rounded.to_eng_string()



    def get_values(self,growth):
        table_name=self.resolve_table()
        table=getattr(growth,table_name)
        if self.chart in ["wfh","wfl"]:
            if D(self.height) < 45:
                raise exceptions.InvalidMeasurement("too short")
            if D(self.height) >120:
                raise exceptions.InvalidMeasurement("too tall")
            closest_height=self.rounded_height
            self.logger.debug("looking up scores with: %s" % closest_height)
            scores = table.get(str(closest_height))
            if scores is not None:
                return scores
            raise exceptions.DataNotFound("SCORES NOT FOUND FOR HEIGHT :%s",(self.closest_height))

        elif self.chart in ['wfa','lhfa']:
            scores=table.get(str(self.age_in_months))
            if scores is not None:
                return scores
            raise exceptions.DataError("SCORES NOT FOUND BY MONTHS : %s",self.age_in_months)

    def resolve_table(self):

        if self.chart == 'wfl' and D(self.height)>110:
            self.logger.warning('too long for recumbent')
            self.table_chart='wfh'
            self.table_age='2_5'
        elif self.chart =='wfh' and D(self.height)<65:
            self.logger.warning('too short for standing')
            self.table_chart='wfl'
            self.table_age='0_2'
        else:
            self.table_chart=self.chart
            if self.chart=='wfl':
                self.table_age='0_2'
            if self.table_chart=='wfh':
                self.table_age='2_5'
            
            

        if self.sex=='M':
            self.table_sex='boys'
        if self.sex=='F':
            self.table_sex='girls'


        if self.chart in ["wfa","lhfa"]:
            self.table_age="0_5"
            self.table_chart=self.chart

        table = "%(table_chart)s_%(table_sex)s_%(table_age)s" %\
                {"table_chart": self.table_chart,
                 "table_sex": self.table_sex,
                 "table_age": self.table_age}
        self.logger.debug(table) 
        return table             
        



class Calculator():

    def __reformat_table(self,table_name):
        list_of_dicts=getattr(self,table_name)
        if 'Length' in list_of_dicts[0]:
            field_name = 'Length'
        elif 'Height' in list_of_dicts[0]:
            field_name = 'Height'
        elif 'Month' in list_of_dicts[0]:
            field_name = 'Month'
        else:
            raise exceptions.DataError('error loading: %s' % table_name)
        new_dict = {'field_name': field_name}
        for d in list_of_dicts:
            new_dict.update({d[field_name]: d})
        setattr(self,table_name,new_dict)



    def __init__(self,logger_name='z_score_log',log_level="INFO"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, log_level))


        WHO_tables = [
            'wfl_boys_0_2_zscores.json',  'wfl_girls_0_2_zscores.json',
            'wfh_boys_2_5_zscores.json',  'wfh_girls_2_5_zscores.json',
            'wfa_boys_0_5_zscores.json',  'wfa_girls_0_5_zscores.json',
            'lhfa_boys_0_5_zscores.json', 'lhfa_girls_0_5_zscores.json',]

        table_dir = os.path.join(module_dir, 'tables')
        table_to_load=WHO_tables

        for table in table_to_load:
            table_file=os.path.join(table_dir,table)
            with open(table_file,'r') as f:
                table_name, underscore, zscore_part =table.split('.')[0].rpartition('_')
                setattr(self, table_name, json.load(f))
                self.__reformat_table(table_name)




    def zScore_wfa(self,weight=None,muac=None,age_in_months=None,sex=None,height=None):
        return self.z_score_measurement('wfa',weight=weight,muac=None,age_in_months=age_in_months,sex=sex,height=None)

    def zScore_wfl(self,weight=None,muac=None,age_in_months=None,sex=None,height=None):
        if(D(age_in_months)>24):
            return self.zScore_wfh(weight,muac,age_in_months,sex,height)
        return self.z_score_measurement('wfl',weight=weight,muac=None,age_in_months=age_in_months,sex=sex,height=height)

    def zScore_wfh(self,weight=None,muac=None,age_in_months=None,sex=None,height=None):
        if(D(age_in_months) <= 24):
            return self.zScore_wfl(weight,muac,age_in_months,sex,height)
        return self.z_score_measurement('wfh',weight=weight,muac=None,age_in_months=age_in_months,sex=sex,height=height)

    def zScore_lhfa(self,weight=None,muac=None,age_in_months=None,sex=None,height=None):
        return self.z_score_measurement('lhfa',weight=None,muac=None,age_in_months=age_in_months,sex=sex,height=height)
        
    def zScore(self,weight=None,muac=None,age_in_months=None,sex=None,height=None):
        wfa=self.zScore_wfa(weight=weight,age_in_months=age_in_months,sex=sex)
        dummy=''
        if(D(age_in_months)>24):
            dummy='Z_score_WFH'
            wfl=self.zScore_wfh(weight=weight,age_in_months=age_in_months,sex=sex,height=height)
        else:
            dummy='Z_score_WFL'
            wfl=self.zScore_wfl(weight=weight,age_in_months=age_in_months,sex=sex,height=height)
        lhfa=self.zScore_lhfa(age_in_months=age_in_months,sex=sex,height=height)
        zscore=json.dumps({'Z_score_WFA':wfa,dummy:wfl,"Z_score_HFA":lhfa})
        return zscore

    def zScore_withclass(self,weight=None,muac=None,age_in_months=None,sex=None,height=None):
        wfa=self.zScore_wfa(weight=weight,age_in_months=age_in_months,sex=sex)
        if wfa < -3:
            class_wfa='Severly Under-weight'
        elif wfa >= -3 and wfa < -2:
            class_wfa='Moderately Under-weight'
        else:
            class_wfa='Healthy'

        dummy=''
        dummy_class=""
        if(D(age_in_months)>24):
            dummy='Z_score_WFH'
            dummy_class="Class_WFH"
            wfl=self.zScore_wfh(weight=weight,age_in_months=age_in_months,sex=sex,height=height)
        else:
            dummy='Z_score_WFL'
            dummy_class="Class_WFL"
            wfl=self.zScore_wfl(weight=weight,age_in_months=age_in_months,sex=sex,height=height)
        class_wfl=self.SAM_MAM(weight,muac,age_in_months,sex,height)


        lhfa=self.zScore_lhfa(age_in_months=age_in_months,sex=sex,height=height)
        if lhfa < -3:
            class_lhfa='Severly Stunted'
        elif lhfa >= -3 and lhfa < -2:
            class_lhfa='Moderately Stunted'
        else:
            class_lhfa='Healthy'

        zscore=json.dumps({'Z_score_WFA':wfa,'Class_WFA':class_wfa,dummy:wfl,dummy_class:class_wfl,'Z_score_HFA':lhfa,'Class_HFA':class_lhfa})
        return zscore

    def SAM_MAM(self,weight=None,muac=None,age_in_months=None,sex=None,height=None):
        assert muac is not None

        if(D(age_in_months)>24):
            wfl=self.zScore_wfh(weight=weight,age_in_months=age_in_months,sex=sex,height=height)
        else:
            wfl=self.zScore_wfl(weight=weight,age_in_months=age_in_months,sex=sex,height=height)
        if(wfl < -3 or D(muac)<11.5):
            return "SAM"
        elif ((wfl >= -3 and wfl<-2) or D(muac)<12.5):
            return "MAM"
        else:
            return "Healthy"



    

    def z_score_measurement(self,chart,weight,muac,age_in_months,sex,height):
        assert sex is not None
        assert sex.upper() in ["M","F"]
        assert age_in_months is not None
        assert chart is not None
        assert chart.lower() in ['wfa','wfh','wfl','lhfa']


        obs = Observation(chart, weight,muac, age_in_months, sex, height,self.logger.name)
        value=obs.get_values(self)

        skew=D(value.get("L"))
        self.logger.debug("BOX-COX: %d" % skew)
        median=D(value.get("M"))
        self.logger.debug("BOX-COX: %d" % median)
        cofficient=D(value.get("S"))
        self.logger.debug("BOX-COX: %d" % cofficient)

        ###
        #  Z score
        #          [y/M(t)]^L(t) - 1
        #   Zind =  -----------------
        #               S(t)L(t)
        ###
        if(chart=='wfa' or chart=='wfl' or chart =='wfh'):
            y=D(weight)
            self.logger.debug("Weight: %d" % y)
        elif(chart=='lhfa'):
            y=D(height)
            self.logger.debug("height: %d" % y)




        numerator=((y/median)**skew)-D(1.0)
        self.logger.debug("NUMERATOR: %d" % numerator)
        denomenator=skew*cofficient
        self.logger.debug("DENOMENATOR: %d" % denomenator)
        zScore=numerator/denomenator
        self.logger.debug("ZSCORE: %d" % zScore)


        #            _
        #           |
        #           |       Zind            if |Zind| <= 3
        #           |
        #           |
        #           |       y - SD3pos
        #   Zind* = | 3 + ( ----------- )   if Zind > 3
        #           |         SD23pos
        #           |
        #           |
        #           |
        #           |        y - SD3neg
        #           | -3 + ( ----------- )  if Zind < -3
        #           |          SD23neg
        #           |
        #           |_

        def calc_stdev(sd):
            value=(1+(skew*cofficient*sd))**(1/skew)
            stdev=median*value
            return stdev

        if(zScore>3):
            SD2pos=calc_stdev(2)
            SD3pos=calc_stdev(3)
            
            SD23pos=SD3pos-SD2pos

            zScore=3+((y-SD3pos)/SD23pos)

            zScore=float(zScore.quantize(D('0.01')))

        elif(zScore<-3):
            SD2neg=calc_stdev(-2)
            SD3neg=calc_stdev(-3)

            SD23neg=SD2neg-SD3neg

            zScore=-3+((y-SD3neg)/SD23neg)
            zScore=float(zScore.quantize(D('0.01')))

        else:
            zScore=float(zScore.quantize(D('0.01')))
            
        return zScore