import functools
import logging
from datetime import datetime
from numbers import Number
from typing import Union, Iterable

import numpy as np
import pandas as pd
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta


class DateUtilWrapper:
    _used_attributes: tuple = ()

    def __init__(self, date: datetime):
        self._date = date

    def __getattr__(self, item: str):
        if item in self._used_attributes:
            return getattr(self._date, item)
        return super().__getattribute__(item)


class TimeStamp(DateUtilWrapper):
    _used_attributes = ('year', 'month', 'day', '__str__', '__repr__')

    def __init__(self, date: datetime):
        self._date = date

    @property
    def date(self) -> datetime:
        return self._date

    @classmethod
    def parse(cls, text_repr: str):
        return cls(parse(text_repr))

    def __le__(self, other: 'TimeStamp'):
        return self._comparison(other, '__le__')

    def __ge__(self, other: 'TimeStamp'):
        return self._comparison(other, '__ge__')

    def __gt__(self, other: 'TimeStamp'):
        return self._comparison(other, '__gt__')

    def __lt__(self, other: 'TimeStamp'):
        return self._comparison(other, '__lt__')

    def __repr__(self):
        return f'TimeStamp({self.year}-{self.month}-{self.day})'

    def __eq__(self, other):
        return self._date == other._date

    def __sub__(self, other: 'TimeStamp'):
        if not isinstance(other, TimeStamp):
            return NotImplemented
        return TimeDelta(relativedelta(self._date, other._date))

    def _comparison(self, other: 'TimeStamp', func_name: str):
        return getattr(self._date, func_name)(other._date)


class TimePeriod:
    _used_attributes = ()
    _extension = None

    def __init__(self, date: datetime | Number, *args, **kwargs):
        if not isinstance(date, (datetime, TimeStamp)):
            date = self.__date_from_numbers(date, *args, **kwargs)
        if isinstance(date, TimeStamp):
            date = date._date
        self._date = date

    @classmethod
    def __date_from_numbers(cls, year: int, month: int = 1, day: int = 1):
        return datetime(int(year), int(month), int(day))

    @classmethod
    def from_id(cls, id: str):
        if len(id) == 4:
            return Year(int(id))
        if 'W' in id:
            return Week(*map(int, id.split('W')))
        elif len(id) == 6:
            return Month(int(id[:4]), int(id[4:]))
        elif len(id) == 8:
            return Day(int(id[:4]), int(id[4:6]), int(id[6:]))

    @property
    def id(self):
        raise NotImplementedError('Must be implemented in subclass')

    def __eq__(self, other):
        r = (self._date == other._date)
        r2 = (self._extension == other._extension)
        if not r or not r2:
            pass
        return r and r2

    def __le__(self, other: 'TimePeriod'):
        if isinstance(other, TimeStamp):
            return TimeStamp(self._date) <= other

        return self._date < other._exclusive_end()

    def __ge__(self, other: 'TimePeriod'):
        if isinstance(other, TimeStamp):
            return TimeStamp(self._exclusive_end()) > other
        return self._exclusive_end() > other._date

    def __gt__(self, other: 'TimePeriod'):
        if isinstance(other, TimeStamp):
            return TimeStamp(self._date) > other
        return self._date >= other._exclusive_end()

    def __lt__(self, other: 'TimePeriod'):
        if isinstance(other, TimeStamp):
            return TimeStamp(self._exclusive_end()) <= other
        return self._exclusive_end() <= other._date

    def __sub__(self, other: 'TimePeriod'):
        if not isinstance(other, TimePeriod):
            return NotImplemented
        assert self._extension == other._extension
        return TimeDelta(relativedelta(self._date, other._date))

    def _exclusive_end(self):
        return self._date + self._extension

    def __getattr__(self, item):
        if item in self._used_attributes:
            return getattr(self._date, item)
        return super().__getattribute__(item)

    @property
    def time_delta(self) -> 'TimeDelta':
        return TimeDelta(self._extension)

    @classmethod
    def parse(cls, text_repr: str):
        if 'W' in text_repr:
            return cls.parse_week(text_repr)
        try:
            year = int(text_repr)
            return Year(year)
        except ValueError:
            pass
        default_dates = [datetime(2010, 1, 1), datetime(2009, 11, 10)]
        dates = [parse(text_repr, default=default_date) for default_date in default_dates]
        date = dates[0]
        if dates[0].day == dates[1].day:
            return Day(date)
        elif dates[0].month == dates[1].month:
            return Month(date)
        return Year(date)

    @classmethod
    def parse_week(cls, week: str):
        year, weeknr = week.split('W')
        return Week(int(year), int(weeknr))

    @property
    def start_timestamp(self):
        return TimeStamp(self._date)

    @property
    def end_timestamp(self):
        return TimeStamp(self._exclusive_end())


class Day(TimePeriod):
    _used_attributes = ['year', 'month', 'day']
    _extension = relativedelta(days=1)

    def __repr__(self):
        return f'Day({self.year}-{self.month}-{self.day})'

    def id(self):
        return self._date.strftime('%Y%m%d')

    def topandas(self):
        return pd.Period(year=self.year, month=self.month, day=self.day, freq='D')

    def to_string(self):
        return f'{self.year}-{self.month:02d}-{self.day:02d}'

    @property
    def id(self):
        return self._date.strftime('%Y%m%d')

class Week(TimePeriod):
    _used_attributes = ['year']
    _extension = relativedelta(weeks=1)

    @property
    def id(self):
        return f'{self.year}W{self.week:02d}'

    def to_string(self):
        return f'{self.year}W{self.week}'

    def __init__(self, date, *args, **kwargs):
        if args or kwargs:
            year = date
            week_nr = args[0] if args else kwargs['week']
            self._date = self.__date_from_numbers(year, week_nr)
            self.week = week_nr
        else:
            if isinstance(date, TimeStamp):
                date = date._date
            self.week = date.isocalendar()[1]
            self._date = date

    def __sub__(self, other: 'TimePeriod'):
        if not isinstance(other, TimePeriod):
            return NotImplemented
        assert self._extension == other._extension
        return TimeDelta(self._date - other._date)

    def __str__(self):
        return f'{self.year}W{self.week}'

    __repr__ = __str__

    def __date_from_numbers(cls, year: int, week_nr: int):
        return datetime.strptime(f'{year}-W{week_nr}-1', "%Y-W%W-%w")

    def topandas(self):
        return self.__str__()
        return pd.Period(self._date, freq='W-MON')


class Month(TimePeriod):
    _used_attributes = ['year', 'month']
    _extension = relativedelta(months=1)

    @property
    def id(self):
        return self._date.strftime('%Y%m')

    def to_string(self):
        return f'{self.year}-{self.month:02d}'

    def topandas(self):
        return pd.Period(year=self.year, month=self.month, freq='M')

    def __repr__(self):
        return f'Month({self.year}-{self.month})'


class Year(TimePeriod):
    _used_attributes = ['year']
    _extension = relativedelta(years=1)

    @property
    def id(self):
        return str(self.year)

    def __repr__(self):
        return f'Year({self.year})'

    def topandas(self):
        return pd.Period(year=self.year, freq='Y')

    def to_string(self):
        return f'{self.year}'


class TimeDelta(DateUtilWrapper):
    def __init__(self, relative_delta: relativedelta):
        self._relative_delta = relative_delta
        self._date = None

    def __eq__(self, other):
        return self._relative_delta == other._relative_delta

    def __add__(self, other: Union[TimeStamp, TimePeriod]):
        if not isinstance(other, (TimeStamp, TimePeriod)):
            return NotImplemented
        return other.__class__(other._date + self._relative_delta)

    def __radd__(self, other: Union[TimeStamp, TimePeriod]):
        return self.__add__(other)

    def __sub__(self, other: Union[TimeStamp, TimePeriod]):
        if not isinstance(other, (TimeStamp, TimePeriod)):
            return NotImplemented
        return other.__class__(other._date - self._relative_delta)

    def __rsub__(self, other: Union[TimeStamp, TimePeriod]):
        return self.__sub__(other)

    def __mul__(self, other: int):
        return self.__class__(self._relative_delta * other)

    def __rmul__(self, other: int):
        return self.__mul__(other)

    def _n_months(self):
        return self._relative_delta.months + 12 * self._relative_delta.years

    def __floordiv__(self, divident: 'TimeDelta'):
        if divident._relative_delta.days != 0:
            for name in ('months', 'years'):
                assert not getattr(divident._relative_delta, name, 0) > 0, f'Cannot divide by {divident}'
                assert not getattr(self._relative_delta, name, 0) > 0, f'Cannot divide {self} by {divident}'

            # assert divident._relative_delta.months == 0 and divident._relative_delta.years == 0, f'Cannot divide by {divident}'
            # assert self._relative_delta.months == 0 and self._relative_delta.years == 0, f'Cannot divide {self} by {divident}'
            return self._relative_delta.days // divident._relative_delta.days

        return self._n_months() // divident._n_months()

    def __mod__(self, other: 'TimeDelta'):
        assert other._relative_delta.days == 0
        return self.__class__(relativedelta(months=self._n_months() % other._n_months()))

    def __repr__(self):
        return f'TimeDelta({self._relative_delta})'


class PeriodRange:

    def __init__(self, start_timestamp: TimeStamp, end_timestamp: TimeStamp, time_delta: TimeDelta):
        self._start_timestamp = start_timestamp
        self._end_timestamp = end_timestamp
        self._time_delta = time_delta

    @property
    def month(self):
        return np.array([p.start_timestamp.month for p in self])

    @property
    def year(self):
        return np.array([p.start_timestamp.year for p in self])

    @property
    def delta(self):
        return self._time_delta

    @classmethod
    def from_time_periods(cls, start_period: TimePeriod, end_period: TimePeriod):
        assert start_period.time_delta == end_period.time_delta
        return cls(TimeStamp(start_period._date), TimeStamp(end_period._exclusive_end()), start_period.time_delta)

    @classmethod
    def from_timestamps(cls, start_timestamp: TimeStamp, end_timestamp: TimeStamp, time_delta: TimeDelta):
        return cls(start_timestamp, end_timestamp, time_delta)

    def __len__(self):
        if self._time_delta._relative_delta.days != 0:
            assert self._time_delta._relative_delta.months == 0 and self._time_delta._relative_delta.years == 0
            days = (self._end_timestamp._date - self._start_timestamp._date).days
            return days // self._time_delta._relative_delta.days
        delta = relativedelta(self._end_timestamp._date, self._start_timestamp._date)
        return TimeDelta(delta) // self._time_delta

    def __eq__(self, other: TimePeriod) -> np.ndarray[bool]:
        ''' Check each period in the range for equality to the given period'''
        return self._vectorize('__eq__', other)

    def _vectorize(self, funcname: str, other: TimePeriod):
        if isinstance(other, PeriodRange):
            assert len(self) == len(other)
            return np.array([getattr(period, funcname)(other_period) for period, other_period in zip(self, other)])
        return np.array([getattr(period, funcname)(other) for period in self])

    def __ne__(self, other: TimePeriod) -> np.ndarray[bool]:
        ''' Check each period in the range for inequality to the given period'''
        return self._vectorize('__ne__', other)

    __lt__ = functools.partialmethod(_vectorize, '__lt__')
    __le__ = functools.partialmethod(_vectorize, '__le__')
    __gt__ = functools.partialmethod(_vectorize, '__gt__')
    __ge__ = functools.partialmethod(_vectorize, '__ge__')

    @property
    def _period_class(self):
        if self._time_delta == delta_month:
            return Month
        elif self._time_delta == delta_year:
            return Year
        elif self._time_delta == delta_day:
            return Day
        elif self._time_delta == delta_week:
            return Week
        raise ValueError(f'Unknown time delta {self._time_delta}')

    def __iter__(self):
        return (self._period_class((self._start_timestamp + self._time_delta * i)._date) for i in range(len(self)))

    def __getitem__(self, item: slice | int):
        ''' Slice by numeric index in the period range'''
        if isinstance(item, Number):
            if item < 0:
                item += len(self)
            return self._period_class((self._start_timestamp + self._time_delta * item)._date)
        assert item.step is None
        start = self._start_timestamp
        end = self._end_timestamp
        if item.stop is not None:
            if item.stop < 0:
                end -= self._time_delta * abs(item.stop)
            else:
                end = start + self._time_delta * item.stop  # Not sure about the logic here, test more

        if item.start is not None:
            offset = item.start if item.start >= 0 else len(self) + item.start
            start = start + self._time_delta * offset
        if start > end:
            raise ValueError(f'Invalid slice {item} for period range {self} of length {len(self)}')
        return PeriodRange(start, end, self._time_delta)

    def topandas(self):
        if self._time_delta == delta_month:
            return pd.Series([pd.Period(year=p.year, month=p.month, freq='M') for p in self])
        elif self._time_delta == delta_year:
            return pd.Series([pd.Period(year=p.year, freq='Y') for p in self])
        elif self._time_delta == delta_day:
            return pd.Series([pd.Period(year=p.year, month=p.month, day=p.day, freq='D') for p in self])
        elif self._time_delta == delta_week:
            return pd.Series([p.topandas() for p in self])
        else:
            raise ValueError(f'Cannot convert period range with time delta {self._time_delta} to pandas')

    @classmethod
    def from_pandas(cls, periods: Iterable[pd.Period]):
        time_deltas = {'M': delta_month, 'Y': delta_year, 'D': delta_day}
        periods = list(periods)
        if not len(periods):
            raise ValueError('Cannot create a period range from an empty list')
        frequency = periods[0].freqstr
        time_delta = time_deltas[frequency]
        assert all(p.freqstr == frequency for p in periods), f'All periods must have the same frequency {periods}'
        time_periods = [TimePeriod.parse(str(period)) for period in periods]
        cls._check_consequtive(time_delta, time_periods)
        return cls.from_time_periods(time_periods[0], time_periods[-1])

    @classmethod
    def _check_consequtive(cls, time_delta, time_periods, fill_missing=False):
        is_consec = [p2 == p1 + time_delta for p1, p2 in zip(time_periods, time_periods[1:])]
        if not all(is_consec):
            if fill_missing:
                indices = [(p - time_periods[0]) // time_delta for p in time_periods][:-1]
                mask = np.full((time_periods[-1] - time_periods[0]) // time_delta, True)
                mask[indices] = False
                return np.flatnonzero(mask)

            print(f'Periods {time_periods}')
            mask = ~np.array(list(is_consec))
            print(mask)
            for wrong in np.flatnonzero(mask):
                print(f'Wrong period {time_periods[wrong], time_periods[wrong + 1]} with time delta {time_delta}')
                print(time_periods[wrong] + time_delta, time_periods[wrong + 1])
            raise ValueError(f'Periods must be consecutive.')
        return []

    @classmethod
    def _get_delta(cls, periods: list[TimePeriod]):
        delta = periods[0].time_delta
        if not all(period.time_delta == delta for period in periods):
            raise ValueError(f'All periods must have the same time delta {periods}')
        return delta

    @classmethod
    def from_strings(cls, period_strings: Iterable[str], fill_missing=False):
        periods = [TimePeriod.parse(period_string) for period_string in period_strings]
        delta = cls._get_delta(periods)
        missing = cls._check_consequtive(delta, periods, fill_missing)
        ret = cls.from_time_periods(periods[0], periods[-1])
        if fill_missing:
            return ret, missing
        return ret

    @property
    def shape(self):
        return (len(self),)

    def __repr__(self):
        return f'PeriodRange({self._start_timestamp}, {self._end_timestamp}, {self._time_delta})'

    def searchsorted(self, period: TimePeriod, side='left'):
        ''' Find the index where the period would be inserted to maintain order'''
        if side not in ('left', 'right'):
            raise ValueError(f'Invalid side {side}')
        assert period.time_delta == self._time_delta, (period, self._time_delta)
        n_steps = TimeDelta(relativedelta(period._date, self._start_timestamp._date)) // self._time_delta
        if side == 'right':
            n_steps += 1
        n_steps = min(max(0, n_steps), len(self))  # if period is outside
        return n_steps

    def concatenate(self, other: 'PeriodRange') -> 'PeriodRange':
        assert self._time_delta == other._time_delta
        assert other._start_timestamp == self._end_timestamp, "Can only concnatenate when other starts where self ends"
        return PeriodRange(self._start_timestamp, other._end_timestamp, self._time_delta)

    def __array_function__(self, func, types, args, kwargs):
        if func.__name__ == 'concatenate':
            assert len(args[0]) == 2
            return self.concatenate(args[0][1])
        return NotImplemented

    @property
    def start_timestamp(self):
        return self._start_timestamp

    @property
    def end_timestamp(self):
        return self._end_timestamp

    def todict(self):
        return {'start_timestamp': self._start_timestamp, 'end_timestamp': self._end_timestamp, 'time_delta': self._time_delta}


delta_month = TimeDelta(relativedelta(months=1))
delta_year = TimeDelta(relativedelta(years=1))
delta_day = TimeDelta(relativedelta(days=1))
delta_week = TimeDelta(relativedelta(weeks=1))
